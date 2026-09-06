//! Generated from `backend/zenoh_asyncapi.yaml`. Do not edit manually.
//!
//! Regenerate with `backend/tools/generate_types.sh`. These are the native
//! Zenoh payloads used by `emi_mower_zenoh_gateway`; ROS messages remain ROS IDL.

use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct JoystickCommand {
    pub x: f64,
    pub y: f64,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct ImuTelemetry {
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

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct TelemetryRecord {
    pub mower_id: String,
    pub timestamp: String,
    pub latitude: f64,
    pub longitude: f64,
    pub battery_percentage: i64,
    #[serde(default)]
    pub left_motor_speed: Option<f64>,
    #[serde(default)]
    pub left_motor_direction: Option<i64>,
    #[serde(default)]
    pub right_motor_speed: Option<f64>,
    #[serde(default)]
    pub right_motor_direction: Option<i64>,
    #[serde(default)]
    pub cutting_motor_speed: Option<f64>,
    #[serde(default)]
    pub slippage_detected: Option<bool>,
    #[serde(default)]
    pub imu_data: Option<ImuTelemetry>,
}

pub type TelemetryList = Vec<TelemetryRecord>;

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct MowerCertificateRenewChallengeRequest {}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct MowerCertificateRenewChallengeResponse {
    pub nonce: String,
    pub expires_in: i64,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct MowerCertificateRenewCompleteRequest {
    pub nonce: String,
    pub csr_pem: String,
    pub tpm_signature: String,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct MowerCertificateRenewCompleteResponse {
    pub certificate_pem: String,
    pub ca_chain_pem: String,
    pub expires_at: String,
}
