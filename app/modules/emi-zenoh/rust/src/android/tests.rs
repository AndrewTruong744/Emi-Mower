use super::*;
use jni::{objects::JObject, InitArgsBuilder, JNIVersion, NativeMethod};
use serde_json::{from_slice, json, Value};
use std::{
    env,
    ffi::c_void,
    fs,
    path::PathBuf,
    process::Command,
    sync::mpsc,
    thread,
    time::{Duration, Instant},
};
use tokio::{
    sync::oneshot,
    time::{sleep, timeout},
};
use zenoh::{internal::runtime::RuntimeBuilder, session::init, Config};

fn call(env: &mut JNIEnv, class: &JClass, request: &[u8]) -> Value {
    let request = env.byte_array_from_slice(request).unwrap();
    let result = env
        .call_static_method(class, "call", "([B)[B", &[JValue::Object(&request)])
        .unwrap()
        .l()
        .unwrap();
    from_slice(&env.convert_byte_array(JByteArray::from(result)).unwrap()).unwrap()
}

fn last_event(env: &mut JNIEnv, class: &JClass) -> Vec<u8> {
    let value = env
        .get_static_field(class, "lastEvent", "[B")
        .unwrap()
        .l()
        .unwrap();
    env.convert_byte_array(JByteArray::from(value)).unwrap()
}

fn wait_event(env: &mut JNIEnv, class: &JClass, expected: Value) {
    let deadline = Instant::now() + Duration::from_secs(3);
    loop {
        let event: Value = from_slice(&last_event(env, class)).unwrap_or(Value::Null);
        if event == expected {
            return;
        }
        assert!(
            Instant::now() < deadline,
            "expected {expected}, got {event}"
        );
        thread::sleep(Duration::from_millis(5));
    }
}

#[test]
fn jni_requests_worker_callbacks_and_module_lifecycle() {
    let _guard = crate::tests::TEST_LOCK.lock().unwrap();
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let output = root.join("target/jni-test-fixture");
    fs::create_dir_all(&output).unwrap();
    let javac = env::var_os("JAVA_HOME")
        .map(|home| PathBuf::from(home).join("bin/javac"))
        .unwrap_or_else(|| PathBuf::from("javac"));
    assert!(Command::new(javac)
        .arg("-d")
        .arg(&output)
        .arg(root.join("tests/fixtures/expo/modules/emizenoh/RustBridge.java"))
        .status()
        .expect("jni-tests requires a JDK; set JAVA_HOME")
        .success());

    let vm = JavaVM::new(
        InitArgsBuilder::new()
            .version(JNIVersion::V8)
            .option("-Xcheck:jni")
            .build()
            .unwrap(),
    )
    .unwrap();
    let mut env = vm.attach_current_thread().unwrap();
    let bytes = fs::read(output.join("expo/modules/emizenoh/RustBridge.class")).unwrap();
    let class = env
        .define_class("expo/modules/emizenoh/RustBridge", &JObject::null(), &bytes)
        .unwrap();
    // Register the actual Rust exports in a real JVM so byte-array handling,
    // exception propagation and worker attachment are checked by -Xcheck:jni.
    env.register_native_methods(
        &class,
        &[
            NativeMethod {
                name: "initialize".into(),
                sig: "()V".into(),
                fn_ptr: Java_expo_modules_emizenoh_RustBridge_initialize as *mut c_void,
            },
            NativeMethod {
                name: "call".into(),
                sig: "([B)[B".into(),
                fn_ptr: Java_expo_modules_emizenoh_RustBridge_call as *mut c_void,
            },
            NativeMethod {
                name: "shutdown".into(),
                sig: "()V".into(),
                fn_ptr: Java_expo_modules_emizenoh_RustBridge_shutdown as *mut c_void,
            },
        ],
    )
    .unwrap();
    env.call_static_method(&class, "initialize", "()V", &[])
        .unwrap();
    let response = call(&mut env, &class, r#"{"op":"草🌱"}"#.as_bytes());
    assert_eq!(response["ok"], false);
    assert!(response["error"].as_str().unwrap().contains("草🌱"));
    assert_eq!(call(&mut env, &class, &[0xff])["ok"], false);
    assert_eq!(call(&mut env, &class, &[0])["ok"], false);

    // Null input raises a Java exception rather than unwinding across JNI.
    assert!(env
        .call_static_method(
            &class,
            "call",
            "([B)[B",
            &[JValue::Object(&JObject::null())]
        )
        .is_err());
    assert!(env.exception_check().unwrap());
    env.exception_clear().unwrap();
    assert_eq!(
        call(
            &mut env,
            &class,
            br#"{"op":"put","session":999,"key":"test","payload":"{}"}"#
        )["ok"],
        false
    );

    let event = json!({"subscriptionId":"1:1","key":"test/草","payload":"🌱\u{0000}","put":true})
        .to_string()
        .into_bytes();
    let delivery = event.clone();
    thread::spawn(move || emit(&delivery)).join().unwrap();
    assert_eq!(last_event(&mut env, &class), event);

    env.call_static_method(&class, "failNextEvent", "()V", &[])
        .unwrap();
    thread::spawn(|| {
        emit(b"listener throws");
        emit(b"worker recovers");
    })
    .join()
    .unwrap();
    assert_eq!(last_event(&mut env, &class), b"worker recovers");

    env.call_static_method(&class, "shutdown", "()V", &[])
        .unwrap();
    assert!(BRIDGE.lock().unwrap().is_none());
    emit(b"must not deliver after shutdown");
    assert_eq!(last_event(&mut env, &class), b"worker recovers");
    env.call_static_method(&class, "initialize", "()V", &[])
        .unwrap();
    thread::spawn(|| emit(b"reinitialized")).join().unwrap();
    assert_eq!(last_event(&mut env, &class), b"reinitialized");

    // Exercise a successful request/reply through JNI against a local router,
    // then verify Android module teardown drops the real session as well.
    let (router, backend, endpoint) = crate::runtime().block_on(async {
        let mut config = Config::default();
        config.insert_json5("mode", "\"router\"").unwrap();
        config
            .insert_json5("scouting/multicast/enabled", "false")
            .unwrap();
        config
            .insert_json5("listen/endpoints", "[\"tcp/127.0.0.1:0\"]")
            .unwrap();
        let mut router = RuntimeBuilder::new(config).build().await.unwrap();
        router.start().await.unwrap();
        let endpoint = router.get_locators()[0].to_string();
        let backend = init(router.clone().into()).await.unwrap();
        (router, backend, endpoint)
    });
    let connected = call(
        &mut env,
        &class,
        json!({"op":"connect","endpoint":endpoint,"root_ca_pem":null})
            .to_string()
            .as_bytes(),
    );
    assert_eq!(connected["ok"], true);
    let id = connected["result"].as_u64().unwrap();
    let queryable = crate::runtime()
        .block_on(async { backend.declare_queryable("test/unicode").await })
        .unwrap();
    let reply = crate::runtime().spawn(async move {
        let query = queryable.recv_async().await.unwrap();
        query.reply("test/unicode", "草🌱").await.unwrap();
    });
    let response = call(
        &mut env,
        &class,
        json!({"op":"query","session":id,"key":"test/unicode","payload":"{}","timeout_ms":3000})
            .to_string()
            .as_bytes(),
    );
    assert_eq!(response, json!({"ok":true,"result":"草🌱"}));
    crate::runtime().block_on(reply).unwrap();

    let slow_queryable = crate::runtime()
        .block_on(async { backend.declare_queryable("test/slow").await })
        .unwrap();
    let fast_queryable = crate::runtime()
        .block_on(async { backend.declare_queryable("test/fast").await })
        .unwrap();
    let command_subscriber = crate::runtime()
        .block_on(async { backend.declare_subscriber("test/command").await })
        .unwrap();
    let (slow_received_tx, slow_received_rx) = mpsc::channel();
    let (release_slow_tx, release_slow_rx) = oneshot::channel();
    let slow_backend = crate::runtime().spawn(async move {
        let query = slow_queryable.recv_async().await.unwrap();
        slow_received_tx.send(()).unwrap();
        release_slow_rx.await.unwrap();
        query.reply("test/slow", "slow 草🌱").await.unwrap();
    });
    let fast_backend = crate::runtime().spawn(async move {
        let query = fast_queryable.recv_async().await.unwrap();
        query.reply("test/fast", "fast 🌱").await.unwrap();
    });

    // Model Expo's I/O pool with concurrent JNI callers. A second query and a
    // publication must finish while the first query is still awaiting a reply.
    let (completed_tx, completed_rx) = mpsc::channel();
    let slow_class = env.new_global_ref(&class).unwrap();
    let slow_tx = completed_tx.clone();
    let slow_caller = thread::spawn(move || {
        let mut env = JVM.get().unwrap().attach_current_thread().unwrap();
        let class: &JClass = slow_class.as_obj().into();
        let response = call(
            &mut env,
            class,
            json!({"op":"query","session":id,"key":"test/slow","payload":"{}","timeout_ms":10000})
                .to_string()
                .as_bytes(),
        );
        slow_tx.send(("slow", response)).unwrap();
    });
    slow_received_rx
        .recv_timeout(Duration::from_secs(3))
        .unwrap();

    let fast_class = env.new_global_ref(&class).unwrap();
    let fast_caller = thread::spawn(move || {
        let mut env = JVM.get().unwrap().attach_current_thread().unwrap();
        let class: &JClass = fast_class.as_obj().into();
        let response = call(
            &mut env,
            class,
            json!({"op":"query","session":id,"key":"test/fast","payload":"{}","timeout_ms":3000})
                .to_string()
                .as_bytes(),
        );
        completed_tx.send(("fast", response)).unwrap();
    });
    assert_eq!(
        completed_rx.recv_timeout(Duration::from_secs(3)).unwrap(),
        ("fast", json!({"ok":true,"result":"fast 🌱"}))
    );
    assert!(matches!(
        completed_rx.try_recv(),
        Err(mpsc::TryRecvError::Empty)
    ));

    let published = call(
        &mut env,
        &class,
        json!({"op":"put","session":id,"key":"test/command","payload":"{}"})
            .to_string()
            .as_bytes(),
    );
    assert_eq!(published["ok"], true);
    crate::runtime().block_on(async {
        timeout(Duration::from_secs(3), command_subscriber.recv_async())
            .await
            .unwrap()
            .unwrap();
    });
    let failed = call(
        &mut env,
        &class,
        json!({"op":"query","session":u64::MAX,"key":"test/fast","payload":"{}","timeout_ms":3000})
            .to_string()
            .as_bytes(),
    );
    assert_eq!(
        failed,
        json!({"ok":false,"error":"Zenoh session is closed"})
    );
    assert!(matches!(
        completed_rx.try_recv(),
        Err(mpsc::TryRecvError::Empty)
    ));

    release_slow_tx.send(()).unwrap();
    assert_eq!(
        completed_rx.recv_timeout(Duration::from_secs(3)).unwrap(),
        ("slow", json!({"ok":true,"result":"slow 草🌱"}))
    );
    slow_caller.join().unwrap();
    fast_caller.join().unwrap();
    crate::runtime().block_on(async {
        slow_backend.await.unwrap();
        fast_backend.await.unwrap();
    });

    // The app retains callback IDs only. Rust must replay both normal and
    // historical liveliness declarations without any specs supplied by JS.
    let token = crate::runtime().block_on(async {
        backend
            .liveliness()
            .declare_token("test/liveliness")
            .await
            .unwrap()
    });
    for (subscription_id, key, kind) in [
        ("telemetry", "test/telemetry", "data"),
        ("liveliness", "test/liveliness", "liveliness"),
    ] {
        assert_eq!(
            call(
                &mut env,
                &class,
                json!({
                    "op":"subscribe", "session":id, "subscription_id":subscription_id,
                    "key":key, "kind":kind,
                })
                .to_string()
                .as_bytes()
            )["ok"],
            true
        );
    }
    let live_event =
        json!({"subscriptionId":"liveliness","key":"test/liveliness","payload":"","put":true});
    wait_event(&mut env, &class, live_event.clone());
    // Retain a stable, known publisher match before asserting sample delivery.
    let publisher = crate::runtime()
        .block_on(async { backend.declare_publisher("test/telemetry").await.unwrap() });
    crate::runtime().block_on(async {
        timeout(Duration::from_secs(3), async {
            while !publisher.matching_status().await.unwrap().matching() {
                sleep(Duration::from_millis(5)).await;
            }
        })
        .await
        .unwrap();
        publisher.put("before 草🌱").await.unwrap();
    });
    wait_event(
        &mut env,
        &class,
        json!({"subscriptionId":"telemetry","key":"test/telemetry","payload":"before 草🌱","put":true}),
    );
    assert_eq!(
        call(
            &mut env,
            &class,
            json!({"op":"restore_subscriptions","session":id})
                .to_string()
                .as_bytes()
        )["ok"],
        true
    );
    wait_event(&mut env, &class, live_event);
    crate::runtime().block_on(async {
        publisher.put("after 🌱").await.unwrap();
    });
    wait_event(
        &mut env,
        &class,
        json!({"subscriptionId":"telemetry","key":"test/telemetry","payload":"after 🌱","put":true}),
    );
    assert_eq!(
        call(
            &mut env,
            &class,
            br#"{"op":"unsubscribe","subscription_id":"telemetry"}"#
        )["ok"],
        true
    );
    assert_eq!(
        call(
            &mut env,
            &class,
            json!({"op":"restore_subscriptions","session":id})
                .to_string()
                .as_bytes()
        )["ok"],
        true
    );
    assert!(!crate::subscribers()
        .lock()
        .unwrap()
        .contains_key("telemetry"));
    drop(token);

    let closing_queryable = crate::runtime()
        .block_on(async { backend.declare_queryable("test/closing").await })
        .unwrap();
    let closing_class = env.new_global_ref(&class).unwrap();
    let (closing_tx, closing_rx) = mpsc::channel();
    let closing_caller = thread::spawn(move || {
        let mut env = JVM.get().unwrap().attach_current_thread().unwrap();
        let class: &JClass = closing_class.as_obj().into();
        let response = call(
            &mut env,
            class,
            json!({"op":"query","session":id,"key":"test/closing","payload":"{}","timeout_ms":10000})
                .to_string()
                .as_bytes(),
        );
        closing_tx.send(response).unwrap();
    });
    let held_query = crate::runtime().block_on(async {
        timeout(Duration::from_secs(3), closing_queryable.recv_async())
            .await
            .unwrap()
            .unwrap()
    });
    env.call_static_method(&class, "shutdown", "()V", &[])
        .unwrap();
    assert!(crate::session(id).is_err());
    assert!(crate::subscribers().lock().unwrap().is_empty());
    assert_eq!(
        call(
            &mut env,
            &class,
            json!({"op":"restore_subscriptions","session":id})
                .to_string()
                .as_bytes()
        )["ok"],
        false
    );
    let interrupted = closing_rx.recv_timeout(Duration::from_secs(3)).unwrap();
    assert_eq!(interrupted["ok"], false);
    assert!(interrupted["error"].as_str().is_some());
    closing_caller.join().unwrap();
    drop(held_query);
    crate::runtime().block_on(async {
        backend.close().await.unwrap();
        router.close().await.unwrap();
    });
}
