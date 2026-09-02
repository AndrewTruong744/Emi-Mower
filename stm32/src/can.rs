//! CAN 2.0 control frame validation and the independent MCU watchdog.

/// Standard 11-bit CAN ID for teleoperation commands from the Jetson.
pub const CAN_COMMAND_ID: u16 = 0x321;
pub const CAN_PROTOCOL_VERSION: u8 = 1;
pub const CAN_FRAME_LEN: usize = 8;
pub const COMMAND_TIMEOUT_MS: u32 = 200;

/// Decoded classic-CAN control frame.
///
/// Wire layout: `version | flags | sequence | linear_mm_s:i16le |
/// angular_mrad_s:i16le | crc8_atm`. `flags & 1` is the enable bit. All other
/// flag bits must be zero. A disabled frame is intentionally a valid stop.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct CanCommandFrame {
    pub enabled: bool,
    pub sequence: u8,
    pub linear_mm_s: i16,
    pub angular_mrad_s: i16,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FrameError {
    BadLength,
    BadVersion,
    BadFlags,
    BadChecksum,
    StaleSequence,
}

impl CanCommandFrame {
    pub const STOP: Self = Self {
        enabled: false,
        sequence: 0,
        linear_mm_s: 0,
        angular_mrad_s: 0,
    };

    pub const fn new(enabled: bool, sequence: u8, linear_mm_s: i16, angular_mrad_s: i16) -> Self {
        Self {
            enabled,
            sequence,
            linear_mm_s,
            angular_mrad_s,
        }
    }

    pub fn encode(self) -> [u8; CAN_FRAME_LEN] {
        let mut bytes = [0; CAN_FRAME_LEN];
        bytes[0] = CAN_PROTOCOL_VERSION;
        bytes[1] = u8::from(self.enabled);
        bytes[2] = self.sequence;
        bytes[3..5].copy_from_slice(&self.linear_mm_s.to_le_bytes());
        bytes[5..7].copy_from_slice(&self.angular_mrad_s.to_le_bytes());
        bytes[7] = crc8_atm(&bytes[..7]);
        bytes
    }

    pub fn decode(bytes: &[u8]) -> Result<Self, FrameError> {
        if bytes.len() != CAN_FRAME_LEN {
            return Err(FrameError::BadLength);
        }
        if bytes[0] != CAN_PROTOCOL_VERSION {
            return Err(FrameError::BadVersion);
        }
        if bytes[1] & !1 != 0 {
            return Err(FrameError::BadFlags);
        }
        if crc8_atm(&bytes[..7]) != bytes[7] {
            return Err(FrameError::BadChecksum);
        }
        Ok(Self {
            enabled: bytes[1] == 1,
            sequence: bytes[2],
            linear_mm_s: i16::from_le_bytes([bytes[3], bytes[4]]),
            angular_mrad_s: i16::from_le_bytes([bytes[5], bytes[6]]),
        })
    }
}

/// CRC-8/ATM, initialized to zero, over bytes 0 through 6.
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

/// Owns the MCU-side sequence check and command timeout.
#[derive(Clone, Copy, Debug)]
pub struct CommandReceiver {
    last_sequence: Option<u8>,
    last_command: CanCommandFrame,
    last_received_at_ms: Option<u32>,
    timeout_ms: u32,
}

impl CommandReceiver {
    pub const fn new(timeout_ms: u32) -> Self {
        Self {
            last_sequence: None,
            last_command: CanCommandFrame::STOP,
            last_received_at_ms: None,
            timeout_ms,
        }
    }

    pub const fn with_default_timeout() -> Self {
        Self::new(COMMAND_TIMEOUT_MS)
    }

    /// Accept a valid, newer frame. Sequence numbers are compared modulo 256;
    /// jumps of 128 or more are rejected as ambiguous/replayed.
    pub fn accept(&mut self, frame: CanCommandFrame, now_ms: u32) -> Result<(), FrameError> {
        if let Some(last) = self.last_sequence {
            if !is_newer_sequence(frame.sequence, last) {
                return Err(FrameError::StaleSequence);
            }
        }
        self.last_sequence = Some(frame.sequence);
        self.last_command = frame;
        self.last_received_at_ms = Some(now_ms);
        Ok(())
    }

    /// Returns a safe stop before the first accepted frame, after the watchdog
    /// expires, and whenever the latest frame has disabled the command.
    pub fn command_at(&self, now_ms: u32) -> CanCommandFrame {
        let fresh = self
            .last_received_at_ms
            .map(|received| now_ms.wrapping_sub(received) <= self.timeout_ms)
            .unwrap_or(false);
        if fresh && self.last_command.enabled {
            self.last_command
        } else {
            CanCommandFrame::STOP
        }
    }
}

fn is_newer_sequence(candidate: u8, previous: u8) -> bool {
    let delta = candidate.wrapping_sub(previous);
    delta != 0 && delta < 128
}
