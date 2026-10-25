use super::*;
use serde_json::{from_slice, from_str, from_value, json, Value};
use std::{sync::Barrier, thread};
use tokio::time::{sleep, timeout};
use zenoh::{
    internal::runtime::{ConnectionAuthorization, RuntimeBuilder},
    session::init,
};
pub(super) static TEST_LOCK: Mutex<()> = Mutex::new(());
fn call(request: Value) -> Value {
    from_str(&call_json(request.to_string().as_bytes())).unwrap()
}
#[test]
fn invalid_input_and_closed_sessions() {
    let _guard = TEST_LOCK.lock().unwrap();
    assert!(
        !call(json!({"op":"put","session":999,"key":"mower/A/joystick","payload":"{}"}))["ok"]
            .as_bool()
            .unwrap()
    );
}
#[test]
fn native_session_queries_and_publishes_through_live_authorization() {
    let _guard = TEST_LOCK.lock().unwrap();
    let (router, backend, access, endpoint) = runtime().block_on(async {
        let mut config = Config::default();
        config.insert_json5("mode", "\"router\"").unwrap();
        config.insert_json5("scouting/multicast/enabled", "false").unwrap();
        config.insert_json5("listen/endpoints", "[\"tcp/127.0.0.1:0\"]").unwrap();
        config.insert_json5("access_control", r#"{"enabled":true,"default_permission":"deny","rules":[{"id":"guest","permission":"allow","messages":["query","reply"],"flows":["ingress","egress"],"key_exprs":["user/login"]}],"subjects":[{"id":"guest"}],"policies":[{"id":"guest","subjects":["guest"],"rules":["guest"]}]}"#).unwrap();
        let mut router = RuntimeBuilder::new(config).build().await.unwrap();
        router.start().await.unwrap();
        let access = router.runtime_access_control();
        access.configure_capture(vec!["user/login".try_into().unwrap()]).unwrap();
        let endpoint = router.get_locators()[0].to_string();
        let backend = init(router.clone().into()).await.unwrap();
        (router,backend,access,endpoint)
    });
    // Expo runs native calls concurrently. Exactly one opening attempt may
    // reserve the single session; the other must not create another connection.
    let barrier = Barrier::new(2);
    let connect = || {
        barrier.wait();
        call(json!({"op":"connect","endpoint":endpoint,"root_ca_pem":null}))
    };
    let (first, second) = thread::scope(|scope| {
        let first = scope.spawn(connect);
        let second = scope.spawn(connect);
        (first.join().unwrap(), second.join().unwrap())
    });
    let (opened, rejected) = if first["ok"] == true {
        (first, second)
    } else {
        (second, first)
    };
    assert_eq!(opened["ok"], true);
    assert_eq!(rejected["ok"], false);
    assert!(rejected["error"]
        .as_str()
        .unwrap()
        .contains("already open or opening"));
    let id = opened["result"].as_u64().unwrap();
    // A declaration attempted as a guest is retained locally, but the router
    // cannot forward it. Replay after login must establish the permitted route.
    assert_eq!(
        call(
            json!({"op":"subscribe","session":id,"key":"mower/A/telemetry","subscription_id":"pre-login","kind":"data"})
        )["ok"],
        true
    );
    let telemetry = runtime().block_on(async {
        backend
            .declare_publisher("mower/A/telemetry")
            .await
            .unwrap()
    });
    let queryable = runtime()
        .block_on(async { backend.declare_queryable("user/login").await })
        .unwrap();
    let authorization = access.clone();
    let login = runtime().spawn(async move {
        let query = queryable.recv_async().await.unwrap();
        let attachment: Value = from_slice(&query.attachment().unwrap().to_bytes()).unwrap();
        let rules = from_value(json!([{"id":"user","permission":"allow","messages":["query","reply","put","declare_subscriber"],"flows":["ingress","egress"],"key_exprs":["user/login","mower/A/**"]}])).unwrap();
        authorization.upsert_principal("alice",rules).unwrap();
        authorization.authorize(attachment["zenoh_connection"]["id"].as_str().unwrap(), ConnectionAuthorization {
            principal:"alice".into(),nonce:attachment["zenoh_connection"]["nonce"].as_str().unwrap().into(),ttl_seconds:300,
        }).unwrap();
        query.reply("user/login", r#"{"authorized":true,"name":"草🌱"}"#).await.unwrap();
    });
    let reply = call(
        json!({"op":"query","session":id,"key":"user/login","payload":"{}","timeout_ms":3000}),
    );
    assert_eq!(reply["ok"], true);
    assert!(reply["result"].as_str().unwrap().contains("草🌱"));
    runtime().block_on(login).unwrap();
    assert_eq!(
        call(json!({"op":"restore_subscriptions","session":id}))["ok"],
        true
    );
    runtime().block_on(async {
        timeout(Duration::from_secs(3), async {
            while !telemetry.matching_status().await.unwrap().matching() {
                sleep(Duration::from_millis(5)).await;
            }
        })
        .await
        .unwrap();
    });
    let receiver = runtime()
        .block_on(async { backend.declare_subscriber("mower/A/joystick").await })
        .unwrap();
    let put =
        call(json!({"op":"put","session":id,"key":"mower/A/joystick","payload":"{\"vx\":0}"}));
    assert_eq!(put["ok"], true);
    runtime().block_on(async {
        assert!(timeout(Duration::from_secs(3), receiver.recv_async())
            .await
            .unwrap()
            .is_ok());
    });
    assert_eq!(access.connections().len(), 1);
    assert_eq!(call(json!({"op":"close","session":id}))["ok"], true);
    assert!(subscribers().lock().unwrap().is_empty());
    let replacement = call(json!({"op":"connect","endpoint":endpoint,"root_ca_pem":null}));
    assert_eq!(replacement["ok"], true);
    let replacement_id = replacement["result"].as_u64().unwrap();
    assert_ne!(id, replacement_id);
    // An old JS account's delayed cleanup must not close the replacement.
    assert_eq!(call(json!({"op":"close","session":id}))["ok"], true);
    assert!(session(id).is_err());
    assert!(session(replacement_id).is_ok());
    assert_eq!(
        call(json!({"op":"restore_subscriptions","session":id}))["ok"],
        false
    );
    assert_eq!(
        call(json!({"op":"close","session":replacement_id}))["ok"],
        true
    );
    runtime().block_on(async {
        backend.close().await.unwrap();
        router.close().await.unwrap();
    });
}
