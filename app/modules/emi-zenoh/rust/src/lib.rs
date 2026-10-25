//! Native Zenoh transport exposed through Android JNI.
#[cfg(any(target_os = "android", feature = "jni-tests"))]
mod android;
#[cfg(feature = "test-driver")]
pub mod test_driver;
use base64::{engine::general_purpose::STANDARD, Engine};
use serde::Deserialize;
use serde_json::{from_slice, json, Value};
use std::{
    collections::HashMap,
    mem::replace,
    panic::catch_unwind,
    sync::{
        atomic::{AtomicU64, Ordering},
        Arc, Mutex, OnceLock,
    },
    time::Duration,
};
use tokio::runtime::{Builder, Runtime};
use zenoh::{
    bytes::Encoding,
    open,
    pubsub::Subscriber,
    sample::{Sample, SampleKind},
    Config, Session,
};
static RUNTIME: OnceLock<Runtime> = OnceLock::new();
enum SessionSlot {
    Empty,
    Opening(u64),
    Open { id: u64, session: Arc<Session> },
}
impl SessionSlot {
    fn is_open(&self, expected: u64) -> bool {
        matches!(self, Self::Open { id, .. } if *id == expected)
    }
}
static SESSION: OnceLock<Mutex<SessionSlot>> = OnceLock::new();

#[derive(Clone, Copy, Deserialize)]
#[serde(rename_all = "snake_case")]
enum SubscriptionKind {
    Data,
    Liveliness,
}
// Native declarations and their replay specifications have one owner. JavaScript
// retains only callbacks indexed by the subscription ID.
struct Subscription {
    key: String,
    kind: SubscriptionKind,
    handle: Mutex<Option<Subscriber<()>>>,
}
type Subscriptions = HashMap<String, Arc<Subscription>>;
static SUBSCRIBERS: OnceLock<Mutex<Subscriptions>> = OnceLock::new();
// IDs distinguish successive sessions, not simultaneous sessions. Late calls
// from a previous account must never operate on its replacement.
static NEXT_SESSION_ID: AtomicU64 = AtomicU64::new(1);
fn runtime() -> &'static Runtime {
    RUNTIME.get_or_init(|| Builder::new_multi_thread().enable_all().build().unwrap())
}
fn session_slot() -> &'static Mutex<SessionSlot> {
    SESSION.get_or_init(|| Mutex::new(SessionSlot::Empty))
}
fn subscribers() -> &'static Mutex<Subscriptions> {
    SUBSCRIBERS.get_or_init(Mutex::default)
}
fn session(id: u64) -> Result<Arc<Session>, String> {
    match &*session_slot().lock().unwrap() {
        SessionSlot::Open {
            id: active,
            session,
        } if *active == id => Ok(session.clone()),
        _ => Err("Zenoh session is closed".into()),
    }
}
fn detach_session(expected: Option<u64>) -> Option<Arc<Session>> {
    let mut active = session_slot().lock().unwrap();
    let id = match &*active {
        SessionSlot::Empty => return None,
        SessionSlot::Opening(id) | SessionSlot::Open { id, .. } => *id,
    };
    if expected.is_some_and(|expected| expected != id) {
        return None;
    }
    let removed = replace(&mut *active, SessionSlot::Empty);
    subscribers().lock().unwrap().clear();
    match removed {
        SessionSlot::Open { session, .. } => Some(session),
        _ => None,
    }
}
async fn close_session(expected: Option<u64>) -> Result<(), String> {
    if let Some(session) = detach_session(expected) {
        session.close().await.map_err(|e| e.to_string())?;
    }
    Ok(())
}
#[derive(Deserialize)]
#[serde(tag = "op", rename_all = "snake_case", deny_unknown_fields)]
enum Request {
    Connect {
        endpoint: String,
        root_ca_pem: Option<String>,
    },
    Query {
        session: u64,
        key: String,
        payload: String,
        timeout_ms: u64,
    },
    Put {
        session: u64,
        key: String,
        payload: String,
    },
    Subscribe {
        session: u64,
        key: String,
        subscription_id: String,
        kind: SubscriptionKind,
    },
    Unsubscribe {
        subscription_id: String,
    },
    RestoreSubscriptions {
        session: u64,
    },
    Close {
        session: u64,
    },
}
fn emit(id: &str, sample: Sample) {
    let event = json!({"subscriptionId":id,"key":sample.key_expr().as_str(),"payload":sample.payload().try_to_string().map(|s|s.into_owned()).unwrap_or_default(),"put":sample.kind()==SampleKind::Put});
    emit_value(event);
}
fn emit_value(event: Value) {
    #[cfg(any(target_os = "android", feature = "jni-tests"))]
    android::emit(event.to_string().as_bytes());
    #[cfg(not(any(target_os = "android", feature = "jni-tests")))]
    let _ = event;
}
async fn declare_subscriber(
    session: &Session,
    id: &str,
    key: &str,
    kind: SubscriptionKind,
) -> Result<Subscriber<()>, String> {
    let id = id.to_owned();
    let callback = move |sample| emit(&id, sample);
    match kind {
        SubscriptionKind::Liveliness => {
            session
                .liveliness()
                .declare_subscriber(key)
                .history(true)
                .callback(callback)
                .await
        }
        SubscriptionKind::Data => session.declare_subscriber(key).callback(callback).await,
    }
    .map_err(|e| e.to_string())
}
async fn execute(request: Request) -> Result<Value, String> {
    match request {
        Request::Connect {
            endpoint,
            root_ca_pem,
        } => {
            if !endpoint.starts_with("tls/") && !endpoint.starts_with("tcp/") {
                return Err("Use a native tls/ or development tcp/ endpoint".into());
            }
            let mut config = Config::default();
            for (key, value) in [
                ("mode", json!("client")),
                ("scouting/multicast/enabled", json!(false)),
                ("scouting/gossip/enabled", json!(false)),
                ("connect/endpoints", json!([endpoint])),
            ] {
                config
                    .insert_json5(key, &value.to_string())
                    .map_err(|e| e.to_string())?;
            }
            if let Some(pem) = root_ca_pem {
                config
                    .insert_json5(
                        "transport/link/tls/root_ca_certificate_base64",
                        &json!(STANDARD.encode(pem)).to_string(),
                    )
                    .map_err(|e| e.to_string())?;
            }
            let id = NEXT_SESSION_ID.fetch_add(1, Ordering::Relaxed);
            {
                let mut active = session_slot().lock().unwrap();
                if !matches!(*active, SessionSlot::Empty) {
                    return Err("A Zenoh session is already open or opening".into());
                }
                *active = SessionSlot::Opening(id);
            }
            let result = async {
                let opened = open(config).await.map_err(|e| e.to_string())?;
                opened.info().transport_events_listener().callback(move |event| {
                    emit_value(json!({"subscriptionId":format!("@transport:{id}"),"key":"","payload":"","put":event.kind()==SampleKind::Put}));
                }).background().await.map_err(|e| e.to_string())?;
                Ok::<_, String>(Arc::new(opened))
            }.await;
            let retained = {
                let mut active = session_slot().lock().unwrap();
                if matches!(*active, SessionSlot::Opening(opening) if opening == id) {
                    *active = match &result {
                        Ok(session) => SessionSlot::Open {
                            id,
                            session: session.clone(),
                        },
                        Err(_) => SessionSlot::Empty,
                    };
                    true
                } else {
                    false
                }
            };
            let opened = result?;
            if !retained {
                opened.close().await.map_err(|e| e.to_string())?;
                return Err("Zenoh connection attempt was cancelled".into());
            }
            Ok(json!(id))
        }
        Request::Query {
            session: id,
            key,
            payload,
            timeout_ms,
        } => {
            let session = session(id)?;
            let receiver = session
                .get(key)
                .payload(payload)
                .encoding(Encoding::APPLICATION_JSON)
                .timeout(Duration::from_millis(timeout_ms.clamp(1, 60_000)))
                .await
                .map_err(|e| e.to_string())?;
            let reply = receiver
                .recv_async()
                .await
                .map_err(|_| "Zenoh returned no response".to_string())?;
            match reply.result() {
                Ok(sample) => Ok(json!(sample
                    .payload()
                    .try_to_string()
                    .map_err(|e| e.to_string())?)),
                Err(error) => Err(error
                    .payload()
                    .try_to_string()
                    .map(|s| s.into_owned())
                    .unwrap_or_else(|_| "Zenoh request failed".into())),
            }
        }
        Request::Put {
            session: id,
            key,
            payload,
        } => {
            session(id)?
                .put(key, payload)
                .encoding(Encoding::APPLICATION_JSON)
                .await
                .map_err(|e| e.to_string())?;
            Ok(Value::Null)
        }
        Request::Subscribe {
            session: id,
            key,
            subscription_id,
            kind,
        } => {
            let session = session(id)?;
            if subscribers().lock().unwrap().contains_key(&subscription_id) {
                return Err("Subscription already exists".into());
            }
            let subscriber = declare_subscriber(&session, &subscription_id, &key, kind).await?;
            // Closing can race an outstanding subscription creation. Never retain a
            // handle from a session that has already been removed.
            let mut subscriber = Some(subscriber);
            let retained = {
                let active = session_slot().lock().unwrap();
                let mut subscriptions = subscribers().lock().unwrap();
                if active.is_open(id) && !subscriptions.contains_key(&subscription_id) {
                    subscriptions.insert(
                        subscription_id,
                        Arc::new(Subscription {
                            key,
                            kind,
                            handle: Mutex::new(subscriber.take()),
                        }),
                    );
                    true
                } else {
                    false
                }
            };
            if !retained {
                subscriber
                    .unwrap()
                    .undeclare()
                    .await
                    .map_err(|e| e.to_string())?;
                return Err("Zenoh session is closed or subscription already exists".into());
            }
            Ok(Value::Null)
        }
        Request::Unsubscribe { subscription_id } => {
            let removed = subscribers().lock().unwrap().remove(&subscription_id);
            if let Some(subscription) = removed {
                let handle = subscription.handle.lock().unwrap().take();
                if let Some(handle) = handle {
                    handle.undeclare().await.map_err(|e| e.to_string())?;
                }
            }
            Ok(Value::Null)
        }
        Request::RestoreSubscriptions { session: id } => {
            let session = session(id)?;
            let restoring: Vec<_> = {
                let active = session_slot().lock().unwrap();
                if !active.is_open(id) {
                    return Err("Zenoh session is closed".into());
                }
                subscribers()
                    .lock()
                    .unwrap()
                    .iter()
                    .map(|(key, subscription)| (key.clone(), subscription.clone()))
                    .collect()
            };
            for (key, subscription) in restoring {
                let old = subscription.handle.lock().unwrap().take();
                if let Some(old) = old {
                    old.undeclare().await.map_err(|e| e.to_string())?;
                }
                let mut replacement = Some(
                    declare_subscriber(&session, &key, &subscription.key, subscription.kind)
                        .await?,
                );
                // Unsubscribe/close may race replay. Never resurrect a removed
                // subscription, even if its ID was reused for a new declaration.
                {
                    let active = session_slot().lock().unwrap();
                    let subscriptions = subscribers().lock().unwrap();
                    if active.is_open(id)
                        && subscriptions
                            .get(&key)
                            .is_some_and(|current| Arc::ptr_eq(current, &subscription))
                    {
                        *subscription.handle.lock().unwrap() = replacement.take();
                    }
                }
                if let Some(replacement) = replacement {
                    replacement.undeclare().await.map_err(|e| e.to_string())?;
                }
            }
            Ok(Value::Null)
        }
        Request::Close { session: id } => {
            close_session(Some(id)).await?;
            Ok(Value::Null)
        }
    }
}
/// Detach the module's session synchronously; close its network transport
/// on Rust workers without blocking Android's module teardown/UI thread.
#[cfg(any(target_os = "android", feature = "jni-tests"))]
fn shutdown() {
    let active = detach_session(None);
    runtime().spawn(async move {
        if let Some(session) = active {
            let _ = session.close().await;
        }
    });
}
/// Execute a JSON request through the same transport used by Android JNI.
pub fn call_json(request: &[u8]) -> String {
    let result = catch_unwind(|| {
        let request = from_slice(request).map_err(|e| e.to_string())?;
        runtime().block_on(execute(request))
    })
    .unwrap_or_else(|_| Err("Native Zenoh operation failed".into()));
    let response = match result {
        Ok(result) => json!({"ok":true,"result":result}),
        Err(error) => json!({"ok":false,"error":error}),
    };
    response.to_string()
}
#[cfg(test)]
mod tests;
