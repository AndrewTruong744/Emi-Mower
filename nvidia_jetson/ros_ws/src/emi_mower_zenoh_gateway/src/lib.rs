//! The native Zenoh contract at the edge of the ROS graph.
//!
//! This crate intentionally contains no motor or camera logic. It translates
//! the app/backend-facing AsyncAPI routes into typed ROS messages and turns
//! typed ROS telemetry back into the generated native Zenoh payload expected
//! by the backend.

use anyhow::{bail, Result};
use chrono::{DateTime, SecondsFormat, Utc};

pub mod generated;
pub mod renewal;

use generated::zenoh::{ImuTelemetry, TelemetryRecord};

pub use generated::zenoh::JoystickCommand;

pub const TELEOP_TOPIC: &str = "/teleop/cmd_vel";
pub const TELEMETRY_TOPIC: &str = "/mower/telemetry";

#[derive(Clone, Debug, PartialEq)]
pub struct RosTelemetryRecord {
    pub timestamp_seconds: i64,
    pub timestamp_nanoseconds: u32,
    pub latitude: f64,
    pub longitude: f64,
    pub battery_percentage: u8,
    pub left_motor_speed: f64,
    pub left_motor_direction: i8,
    pub right_motor_speed: f64,
    pub right_motor_direction: i8,
    pub cutting_motor_speed: f64,
    pub slippage_detected: bool,
    pub imu_data: Option<RosImuTelemetry>,
}

#[derive(Clone, Debug, PartialEq)]
pub struct RosImuTelemetry {
    pub accel_x: f64,
    pub accel_y: f64,
    pub accel_z: f64,
    pub gyro_x: f64,
    pub gyro_y: f64,
    pub gyro_z: f64,
    pub mag_x: f64,
    pub mag_y: f64,
    pub mag_z: f64,
}

/// Create the `TelemetryList` JSON array declared by the backend AsyncAPI.
pub fn telemetry_payload(mower_id: &str, records: &[RosTelemetryRecord]) -> Result<Vec<u8>> {
    validate_mower_id(mower_id)?;

    let records = records
        .iter()
        .map(|record| telemetry_record(mower_id, record))
        .collect::<Result<Vec<_>>>()?;
    Ok(serde_json::to_vec(&records)?)
}

pub fn parse_joystick_payload(payload: &[u8]) -> Result<JoystickCommand> {
    let joystick = serde_json::from_slice::<JoystickCommand>(payload)?;
    for (axis, value) in [("x", joystick.x), ("y", joystick.y)] {
        if !value.is_finite() || !(-1.0..=1.0).contains(&value) {
            bail!("joystick axis {axis} must be finite and in [-1, 1], got {value}");
        }
    }
    Ok(joystick)
}

/// Map the app's horizontal (`x`) and vertical (`y`) axes to ROS velocity.
pub fn joystick_to_velocity(
    command: JoystickCommand,
    max_linear_mps: f64,
    max_angular_radps: f64,
) -> (f64, f64) {
    (command.y * max_linear_mps, command.x * max_angular_radps)
}

pub fn validate_mower_id(mower_id: &str) -> Result<()> {
    if mower_id.is_empty() || mower_id.contains('/') {
        bail!("mower ID must be one non-empty Zenoh path segment");
    }
    Ok(())
}

fn telemetry_record(mower_id: &str, record: &RosTelemetryRecord) -> Result<TelemetryRecord> {
    validate_record(record)?;
    let timestamp =
        DateTime::<Utc>::from_timestamp(record.timestamp_seconds, record.timestamp_nanoseconds)
            .ok_or_else(|| anyhow::anyhow!("telemetry timestamp is out of range"))?
            .to_rfc3339_opts(SecondsFormat::Nanos, true);

    let imu_data = record.imu_data.as_ref().map(imu_telemetry).transpose()?;
    Ok(TelemetryRecord {
        mower_id: mower_id.to_owned(),
        timestamp,
        latitude: record.latitude,
        longitude: record.longitude,
        battery_percentage: i64::from(record.battery_percentage),
        left_motor_speed: Some(record.left_motor_speed),
        left_motor_direction: Some(i64::from(record.left_motor_direction)),
        right_motor_speed: Some(record.right_motor_speed),
        right_motor_direction: Some(i64::from(record.right_motor_direction)),
        cutting_motor_speed: Some(record.cutting_motor_speed),
        slippage_detected: Some(record.slippage_detected),
        imu_data,
    })
}

fn imu_telemetry(imu: &RosImuTelemetry) -> Result<ImuTelemetry> {
    let fields = [
        imu.accel_x,
        imu.accel_y,
        imu.accel_z,
        imu.gyro_x,
        imu.gyro_y,
        imu.gyro_z,
        imu.mag_x,
        imu.mag_y,
        imu.mag_z,
    ];
    if fields.iter().any(|value| !value.is_finite()) {
        bail!("IMU telemetry values must be finite")
    }
    Ok(ImuTelemetry {
        accel_x: imu.accel_x,
        accel_y: imu.accel_y,
        accel_z: imu.accel_z,
        gyro_x: imu.gyro_x,
        gyro_y: imu.gyro_y,
        gyro_z: imu.gyro_z,
        mag_x: imu.mag_x,
        mag_y: imu.mag_y,
        mag_z: imu.mag_z,
    })
}

fn validate_record(record: &RosTelemetryRecord) -> Result<()> {
    let values = [
        record.latitude,
        record.longitude,
        record.left_motor_speed,
        record.right_motor_speed,
        record.cutting_motor_speed,
    ];
    if values.iter().any(|value| !value.is_finite()) {
        bail!("telemetry numeric values must be finite")
    }
    if !(-1..=1).contains(&record.left_motor_direction)
        || !(-1..=1).contains(&record.right_motor_direction)
    {
        bail!("motor direction must be -1, 0, or 1")
    }
    Ok(())
}
