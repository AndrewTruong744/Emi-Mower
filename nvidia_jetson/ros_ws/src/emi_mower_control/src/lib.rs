//! The ROS-to-CAN command contract shared by the Jetson control executables.
//!
//! `stm32_bridge` receives a ROS velocity command and writes a compact,
//! versioned classic-CAN frame that an Embassy task on the STM32 can decode without
//! ROS support. Native Zenoh payloads belong to `emi_mower_zenoh_gateway`.

use std::time::{Duration, Instant};

pub const STM32_CAN_COMMAND_ID: u16 = 0x321;
pub const STM32_CAN_PROTOCOL_VERSION: u8 = 1;
pub const STM32_CAN_FRAME_LEN: usize = 8;

#[derive(Debug, thiserror::Error)]
pub enum ControlError {
    #[error("invalid STM32 frame")]
    InvalidFrame,
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

/// Holds the most recent ROS command and turns it into zero after a deadline.
#[derive(Debug)]
pub struct CommandWatchdog {
    timeout: Duration,
    last: Option<(Instant, VelocityCommand)>,
}

impl CommandWatchdog {
    pub fn new(timeout: Duration) -> Self {
        Self {
            timeout,
            last: None,
        }
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

/// The classic-CAN data frame consumed by the STM32 Embassy task.
///
/// Layout: `version | enabled | sequence:u8 | linear_mm_s:i16le |
/// angular_mrad_s:i16le | crc8_atm`.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Stm32CommandFrame {
    pub enabled: bool,
    pub sequence: u8,
    pub linear_mm_s: i16,
    pub angular_mrad_s: i16,
}

impl Stm32CommandFrame {
    pub fn from_velocity(sequence: u8, enabled: bool, command: VelocityCommand) -> Self {
        Self {
            enabled,
            sequence,
            linear_mm_s: scale_to_i16(command.linear_mps, 1_000.0),
            angular_mrad_s: scale_to_i16(command.angular_radps, 1_000.0),
        }
    }

    pub fn encode(self) -> [u8; STM32_CAN_FRAME_LEN] {
        let mut bytes = [0_u8; STM32_CAN_FRAME_LEN];
        bytes[0] = STM32_CAN_PROTOCOL_VERSION;
        bytes[1] = u8::from(self.enabled);
        bytes[2] = self.sequence;
        bytes[3..5].copy_from_slice(&self.linear_mm_s.to_le_bytes());
        bytes[5..7].copy_from_slice(&self.angular_mrad_s.to_le_bytes());
        bytes[7] = crc8_atm(&bytes[..7]);
        bytes
    }

    pub fn decode(bytes: &[u8]) -> Result<Self, ControlError> {
        if bytes.len() != STM32_CAN_FRAME_LEN
            || bytes[0] != STM32_CAN_PROTOCOL_VERSION
            || bytes[1] > 1
        {
            return Err(ControlError::InvalidFrame);
        }
        if crc8_atm(&bytes[..7]) != bytes[7] {
            return Err(ControlError::InvalidFrame);
        }
        Ok(Self {
            enabled: bytes[1] == 1,
            sequence: bytes[2],
            linear_mm_s: i16::from_le_bytes(bytes[3..5].try_into().unwrap()),
            angular_mrad_s: i16::from_le_bytes(bytes[5..7].try_into().unwrap()),
        })
    }
}

fn scale_to_i16(value: f64, scale: f64) -> i16 {
    (value * scale)
        .round()
        .clamp(i16::MIN as f64, i16::MAX as f64) as i16
}

/// CRC-8/ATM, suitable for both Linux and Embassy.
pub fn crc8_atm(bytes: &[u8]) -> u8 {
    let mut crc = 0_u8;
    for byte in bytes {
        crc ^= *byte;
        for _ in 0..8 {
            crc = if crc & 0x80 != 0 {
                (crc << 1) ^ 0x07
            } else {
                crc << 1
            };
        }
    }
    crc
}
