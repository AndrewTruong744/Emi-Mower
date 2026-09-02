#![cfg_attr(not(test), no_std)]
//! Control logic shared by the Embassy firmware, host tests, and Renode.
//!
//! This crate deliberately does not contain ROS 2. The Jetson ROS bridge turns
//! `/teleop/cmd_vel` into a CAN frame; the MCU only accepts that bounded,
//! authenticated-by-CRC control message and remains the final safety authority.

pub mod can;
pub mod skid_steer;

pub use can::{CAN_COMMAND_ID, CAN_FRAME_LEN, CanCommandFrame, CommandReceiver, FrameError};
pub use skid_steer::{MotorCommand, SkidSteerConfig, SkidSteerMixer};
