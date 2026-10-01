use emi_mower_zenoh_gateway::generated::zenoh::TelemetryRecord;
use emi_mower_zenoh_gateway::generated::zenoh_paths::{
    mower_cutout_delivery_path, mower_joystick_path, mower_liveliness_path,
    MOWER_CUTOUT_DELIVERY_ADDRESS, MOWER_JOYSTICK_ADDRESS, MOWER_LIVELINESS_ADDRESS,
};
use emi_mower_zenoh_gateway::{
    joystick_to_velocity, parse_cutout_delivery, parse_joystick_payload, telemetry_payload,
    validate_mower_id, RosImuTelemetry, RosTelemetryRecord,
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
fn generated_liveliness_route_is_scoped_to_one_mower() {
    assert_eq!(MOWER_LIVELINESS_ADDRESS, "mower/{mower_id}/liveliness");
    assert_eq!(
        mower_liveliness_path("mower-01"),
        "mower/mower-01/liveliness"
    );
}

#[test]
fn generated_cutout_delivery_is_validated_before_ros_publication() {
    assert_eq!(
        MOWER_CUTOUT_DELIVERY_ADDRESS,
        "mower/{mower_id}/cutout/delivery"
    );
    assert_eq!(
        mower_cutout_delivery_path("mower-01"),
        "mower/mower-01/cutout/delivery"
    );
    let response = parse_cutout_delivery(
        br#"{"cutout_id":"cutout-01","download_url":"https://storage.example/cutout","expires_in":300,"content_type":"image/png"}"#,
    )
    .unwrap();
    assert_eq!(response.cutout_id, "cutout-01");
    assert!(parse_cutout_delivery(
        br#"{"cutout_id":"../cutout","download_url":"https://storage.example/cutout","expires_in":300,"content_type":"image/png"}"#,
    )
    .is_err());
    assert!(parse_cutout_delivery(
        br#"{"cutout_id":"cutout-01","download_url":"https://","expires_in":300,"content_type":"image/png"}"#,
    )
    .is_err());
}

#[test]
fn generated_joystick_contract_drives_the_ros_velocity_convention() {
    let joystick = parse_joystick_payload(br#"{"x":0.5,"y":-0.25}"#).unwrap();
    assert_eq!(MOWER_JOYSTICK_ADDRESS, "mower/{mower_id}/joystick");
    assert_eq!(mower_joystick_path("mower-01"), "mower/mower-01/joystick");
    assert_eq!(joystick_to_velocity(joystick, 2.0, 1.5), (-0.5, 0.75));
    assert!(parse_joystick_payload(br#"{"x":1.1,"y":0.0}"#).is_err());
    assert!(parse_joystick_payload(br#"{"x":0.0,"y":0.0,"extra":true}"#).is_ok());
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

#[test]
fn generated_telemetry_type_applies_wire_defaults_and_accepts_extensions() {
    let record: TelemetryRecord = serde_json::from_str(
        r#"{"mower_id":"mower-01","timestamp":"2026-08-16T12:00:00Z","latitude":30.0,"longitude":-97.0,"battery_percentage":87}"#,
    )
    .unwrap();
    assert_eq!(record.left_motor_speed, 0.0);
    assert_eq!(record.left_motor_direction, 0);
    assert!(!record.slippage_detected);
    let extended: TelemetryRecord = serde_json::from_str(
        r#"{"mower_id":"mower-01","timestamp":"2026-08-16T12:00:00Z","latitude":30.0,"longitude":-97.0,"battery_percentage":87,"future_field":true}"#,
    )
    .unwrap();
    assert_eq!(extended.mower_id, record.mower_id);
}
