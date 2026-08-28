use emi_mower_control::{joystick_key, ZENOH_VERSION};

#[test]
fn joystick_key_matches_the_asyncapi_contract() {
    assert_eq!(joystick_key("mower-01").unwrap(), "mower/mower-01/joystick");
}

#[test]
fn zenoh_baseline_matches_python_and_router() {
    assert_eq!(ZENOH_VERSION, "1.9.0");
}
