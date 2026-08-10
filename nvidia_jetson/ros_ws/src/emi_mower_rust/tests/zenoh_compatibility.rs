use emi_mower_rust::{livekit_upload_key, ZENOH_VERSION};

#[test]
fn livekit_upload_key_matches_backend_contract() {
    assert_eq!(livekit_upload_key("mower-01"), "mower/mower-01/livekit/upload");
}

#[test]
fn zenoh_baseline_matches_python_and_router() {
    assert_eq!(ZENOH_VERSION, "1.9.0");
}
