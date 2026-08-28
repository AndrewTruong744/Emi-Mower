//! The command contract shared by the Jetson control executables.
//!
//! `teleop_gateway` receives the app's native Zenoh JSON. `stm32_bridge`
//! receives the resulting ROS command and writes a compact, versioned UART
//! frame that an Embassy task on the STM32 can decode without ROS support.

use serde::Deserialize;
use std::time::{Duration, Instant};

pub const ZENOH_VERSION: &str = "1.9.0";
pub const UART_MAGIC: [u8; 2] = *b"EM";
pub const UART_PROTOCOL_VERSION: u8 = 1;
pub const UART_FRAME_LEN: usize = 14;

#[derive(Debug, thiserror::Error)]
pub enum ControlError {
    #[error("mower ID must be one non-empty Zenoh path segment")]
    InvalidMowerId,
    #[error("joystick payload must be valid JSON: {0}")]
    InvalidJson(#[from] serde_json::Error),
    #[error("joystick axis {axis} must be finite and in [-1, 1], got {value}")]
    InvalidAxis { axis: &'static str, value: f64 },
    #[error("invalid STM32 frame")]
    InvalidFrame,
}

#[derive(Clone, Copy, Debug, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct JoystickCommand {
    pub x: f64,
    pub y: f64,
}

impl JoystickCommand {
    pub fn validate(self) -> Result<Self, ControlError> {
        for (axis, value) in [("x", self.x), ("y", self.y)] {
            if !value.is_finite() || !(-1.0..=1.0).contains(&value) {
                return Err(ControlError::InvalidAxis { axis, value });
            }
        }
        Ok(self)
    }
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct VelocityCommand {
    pub linear_mps: f64,
    pub angular_radps: f64,
}

impl VelocityCommand {
    pub const ZERO: Self = Self {
        linear_mps: 0.0,
        angular_radps: 0.0,
    };
}

/// Build the exact native Zenoh key declared in `backend/zenoh_asyncapi.yaml`.
pub fn joystick_key(mower_id: &str) -> Result<String, ControlError> {
    if mower_id.is_empty() || mower_id.contains('/') {
        return Err(ControlError::InvalidMowerId);
    }
    Ok(format!("mower/{mower_id}/joystick"))
}

pub fn parse_joystick_payload(payload: &[u8]) -> Result<JoystickCommand, ControlError> {
    serde_json::from_slice::<JoystickCommand>(payload)?.validate()
}

/// Map the app's horizontal (`x`) and vertical (`y`) axes to ROS velocity.
pub fn joystick_to_velocity(
    command: JoystickCommand,
    max_linear_mps: f64,
    max_angular_radps: f64,
) -> VelocityCommand {
    VelocityCommand {
        linear_mps: command.y * max_linear_mps,
        angular_radps: command.x * max_angular_radps,
    }
}

/// Holds the most recent ROS command and turns it into zero after a deadline.
#[derive(Debug)]
pub struct CommandWatchdog {
    timeout: Duration,
    last: Option<(Instant, VelocityCommand)>,
}

impl CommandWatchdog {
    pub fn new(timeout: Duration) -> Self {
        Self { timeout, last: None }
    }

    pub fn update(&mut self, command: VelocityCommand, received_at: Instant) {
        self.last = Some((received_at, command));
    }

    pub fn command_at(&self, now: Instant) -> VelocityCommand {
        self.last
            .filter(|(received_at, _)| now.saturating_duration_since(*received_at) <= self.timeout)
            .map(|(_, command)| command)
            .unwrap_or(VelocityCommand::ZERO)
    }
}

/// The UART frame consumed by the STM32 Embassy task.
///
/// Layout: `EM | version | enabled | sequence:u32le | linear_mm_s:i16le |
/// angular_mrad_s:i16le | crc16_xmodem:u16le`.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Stm32CommandFrame {
    pub enabled: bool,
    pub sequence: u32,
    pub linear_mm_s: i16,
    pub angular_mrad_s: i16,
}

impl Stm32CommandFrame {
    pub fn from_velocity(sequence: u32, enabled: bool, command: VelocityCommand) -> Self {
        Self {
            enabled,
            sequence,
            linear_mm_s: scale_to_i16(command.linear_mps, 1_000.0),
            angular_mrad_s: scale_to_i16(command.angular_radps, 1_000.0),
        }
    }

    pub fn encode(self) -> [u8; UART_FRAME_LEN] {
        let mut bytes = [0_u8; UART_FRAME_LEN];
        bytes[0..2].copy_from_slice(&UART_MAGIC);
        bytes[2] = UART_PROTOCOL_VERSION;
        bytes[3] = u8::from(self.enabled);
        bytes[4..8].copy_from_slice(&self.sequence.to_le_bytes());
        bytes[8..10].copy_from_slice(&self.linear_mm_s.to_le_bytes());
        bytes[10..12].copy_from_slice(&self.angular_mrad_s.to_le_bytes());
        let checksum = crc16_xmodem(&bytes[..12]);
        bytes[12..14].copy_from_slice(&checksum.to_le_bytes());
        bytes
    }

    pub fn decode(bytes: &[u8]) -> Result<Self, ControlError> {
        if bytes.len() != UART_FRAME_LEN
            || bytes[0..2] != UART_MAGIC
            || bytes[2] != UART_PROTOCOL_VERSION
            || bytes[3] > 1
        {
            return Err(ControlError::InvalidFrame);
        }
        let expected_crc = u16::from_le_bytes([bytes[12], bytes[13]]);
        if crc16_xmodem(&bytes[..12]) != expected_crc {
            return Err(ControlError::InvalidFrame);
        }
        Ok(Self {
            enabled: bytes[3] == 1,
            sequence: u32::from_le_bytes(bytes[4..8].try_into().unwrap()),
            linear_mm_s: i16::from_le_bytes(bytes[8..10].try_into().unwrap()),
            angular_mrad_s: i16::from_le_bytes(bytes[10..12].try_into().unwrap()),
        })
    }
}

fn scale_to_i16(value: f64, scale: f64) -> i16 {
    (value * scale)
        .round()
        .clamp(i16::MIN as f64, i16::MAX as f64) as i16
}

/// A small allocation-free checksum suitable for both Linux and Embassy.
pub fn crc16_xmodem(bytes: &[u8]) -> u16 {
    let mut crc = 0_u16;
    for byte in bytes {
        crc ^= u16::from(*byte) << 8;
        for _ in 0..8 {
            crc = if crc & 0x8000 != 0 {
                (crc << 1) ^ 0x1021
            } else {
                crc << 1
            };
        }
    }
    crc
}
