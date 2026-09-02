use emi_mower_zenoh_gateway::generated::zenoh_paths::{
    mower_joystick_path, MOWER_JOYSTICK_ADDRESS,
};
use emi_mower_zenoh_gateway::{
    joystick_to_velocity, parse_joystick_payload, telemetry_payload, validate_mower_id,
    RosImuTelemetry, RosTelemetryRecord,
};
use serde_json::Value;

fn record() -> RosTelemetryRecord {
    RosTelemetryRecord {
        timestamp_seconds: 1_700_000_000,
        timestamp_nanoseconds: 123_000_000,
        latitude: 30.2672,
        longitude: -97.7431,
        battery_percentage: 87,
        left_motor_speed: 0.4,
        left_motor_direction: 1,
        right_motor_speed: 0.4,
        right_motor_direction: 1,
        cutting_motor_speed: 0.0,
        slippage_detected: false,
        imu_data: Some(RosImuTelemetry {
            accel_x: 0.0,
            accel_y: 0.1,
            accel_z: 9.8,
            gyro_x: 0.0,
            gyro_y: 0.0,
            gyro_z: 0.0,
            mag_x: 1.0,
            mag_y: 2.0,
            mag_z: 3.0,
        }),
    }
}

#[test]
fn generated_joystick_contract_drives_the_ros_velocity_convention() {
    let joystick = parse_joystick_payload(br#"{"x":0.5,"y":-0.25}"#).unwrap();
    assert_eq!(MOWER_JOYSTICK_ADDRESS, "mower/{mower_id}/joystick");
    assert_eq!(mower_joystick_path("mower-01"), "mower/mower-01/joystick");
    assert_eq!(joystick_to_velocity(joystick, 2.0, 1.5), (-0.5, 0.75));
    assert!(parse_joystick_payload(br#"{"x":1.1,"y":0.0}"#).is_err());
    assert!(parse_joystick_payload(br#"{"x":0.0,"y":0.0,"extra":true}"#).is_err());
    assert!(validate_mower_id("mower/01").is_err());
}

#[test]
fn typed_ros_telemetry_becomes_the_asyncapi_list_payload() {
    let payload = telemetry_payload("mower-01", &[record()]).unwrap();
    let value: Value = serde_json::from_slice(&payload).unwrap();
    let item = &value[0];
    assert_eq!(item["mower_id"], "mower-01");
    assert_eq!(item["battery_percentage"], 87);
    assert_eq!(item["imu_data"]["accel_z"], 9.8);
    assert!(item["timestamp"].as_str().unwrap().ends_with('Z'));
}

#[test]
fn telemetry_rejects_an_invalid_motor_direction_or_mower_route() {
    let mut invalid = record();
    invalid.left_motor_direction = 2;
    assert!(telemetry_payload("mower-01", &[invalid]).is_err());
    assert!(telemetry_payload("another/mower", &[record()]).is_err());
}
