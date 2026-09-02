//! Fixed-point differential-drive mixing for the two traction motors.

use crate::can::CanCommandFrame;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct MotorCommand {
    /// Signed PWM command in the inclusive range `-max_duty..=max_duty`.
    pub left: i16,
    pub right: i16,
}

impl MotorCommand {
    pub const STOP: Self = Self { left: 0, right: 0 };
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SkidSteerConfig {
    /// Centre-to-centre distance between the left and right contact patches.
    pub track_width_mm: i32,
    /// Linear speed corresponding to full traction PWM.
    pub max_wheel_speed_mm_s: i32,
    /// PWM magnitude exposed to the motor-driver adapter, normally 1000.
    pub max_duty: i16,
}

impl Default for SkidSteerConfig {
    fn default() -> Self {
        Self {
            // Conservative placeholders; set these from the measured mower.
            track_width_mm: 500,
            max_wheel_speed_mm_s: 1_000,
            max_duty: 1_000,
        }
    }
}

pub struct SkidSteerMixer {
    config: SkidSteerConfig,
}

impl SkidSteerMixer {
    pub const fn new(config: SkidSteerConfig) -> Self {
        Self { config }
    }

    pub const fn config(&self) -> SkidSteerConfig {
        self.config
    }

    pub fn mix(&self, command: CanCommandFrame) -> MotorCommand {
        if !command.enabled
            || self.config.track_width_mm <= 0
            || self.config.max_wheel_speed_mm_s <= 0
        {
            return MotorCommand::STOP;
        }

        // v_left/right = v -/+ omega * track_width / 2. angular is mrad/s,
        // so divide by 2000 to obtain mm/s without floating-point hardware.
        let turn_mm_s = i32::from(command.angular_mrad_s) * self.config.track_width_mm / 2_000;
        let left_mm_s = i32::from(command.linear_mm_s) - turn_mm_s;
        let right_mm_s = i32::from(command.linear_mm_s) + turn_mm_s;
        MotorCommand {
            left: self.to_duty(left_mm_s),
            right: self.to_duty(right_mm_s),
        }
    }

    fn to_duty(&self, speed_mm_s: i32) -> i16 {
        let scaled =
            speed_mm_s * i32::from(self.config.max_duty) / self.config.max_wheel_speed_mm_s;
        scaled.clamp(
            -i32::from(self.config.max_duty),
            i32::from(self.config.max_duty),
        ) as i16
    }
}
