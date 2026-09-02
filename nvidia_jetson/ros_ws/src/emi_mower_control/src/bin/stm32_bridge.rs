//! Convert safe ROS velocity commands into the STM32's Embassy CAN protocol.

use anyhow::{Context, Result};
use emi_mower_control::{
    CommandWatchdog, Stm32CommandFrame, VelocityCommand, STM32_CAN_COMMAND_ID,
};
use geometry_msgs::msg::TwistStamped;
use rclrs::{Context as RosContext, CreateBasicExecutor, RclrsErrorFilter, SpinOptions};
use socketcan::{CanFrame, CanSocket, Frame as _, Socket as _};
use std::env;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};

fn main() -> Result<()> {
    let interface = env::var("STM32_CAN_INTERFACE").unwrap_or_else(|_| "can0".to_owned());
    let timeout = Duration::from_millis(env_number("COMMAND_TIMEOUT_MS", 200_u64)?);
    let max_linear_mps = env_number("MAX_LINEAR_MPS", 1.0_f64)?;
    let max_angular_radps = env_number("MAX_ANGULAR_RADPS", 1.0_f64)?;
    if !max_linear_mps.is_finite()
        || !max_angular_radps.is_finite()
        || max_linear_mps <= 0.0
        || max_angular_radps <= 0.0
    {
        anyhow::bail!("MAX_LINEAR_MPS and MAX_ANGULAR_RADPS must be finite positive values");
    }
    let state = Arc::new(Mutex::new(CommandWatchdog::new(timeout)));

    let ros_context = RosContext::default_from_env().context("initialize ROS context")?;
    let mut executor = ros_context.create_basic_executor();
    let node = executor
        .create_node("stm32_bridge")
        .context("create STM32 bridge ROS node")?;
    let callback_state = Arc::clone(&state);
    let _subscription = node
        .create_subscription("/teleop/cmd_vel", move |message: TwistStamped| {
            let command = VelocityCommand {
                linear_mps: message.twist.linear.x,
                angular_radps: message.twist.angular.z,
            };
            if command.linear_mps.is_finite() && command.angular_radps.is_finite() {
                if let Ok(mut watchdog) = callback_state.lock() {
                    watchdog.update(
                        VelocityCommand {
                            linear_mps: command.linear_mps.clamp(-max_linear_mps, max_linear_mps),
                            angular_radps: command
                                .angular_radps
                                .clamp(-max_angular_radps, max_angular_radps),
                        },
                        Instant::now(),
                    );
                }
            }
        })
        .context("subscribe to /teleop/cmd_vel")?;

    let can_state = Arc::clone(&state);
    thread::spawn(move || {
        if let Err(error) = write_can_frames(&interface, can_state) {
            eprintln!("STM32 CAN bridge stopped: {error:#}");
        }
    });

    executor.spin(SpinOptions::default()).first_error()?;
    Ok(())
}

fn write_can_frames(interface: &str, state: Arc<Mutex<CommandWatchdog>>) -> Result<()> {
    let socket = CanSocket::open(interface)
        .with_context(|| format!("open STM32 SocketCAN interface {interface}"))?;
    let mut sequence = 0_u8;
    let interval = Duration::from_millis(20);

    loop {
        let command = state
            .lock()
            .map(|watchdog| watchdog.command_at(Instant::now()))
            .unwrap_or(VelocityCommand::ZERO);
        let enabled = command != VelocityCommand::ZERO;
        let data = Stm32CommandFrame::from_velocity(sequence, enabled, command).encode();
        let frame = CanFrame::from_raw_id(u32::from(STM32_CAN_COMMAND_ID), &data)
            .expect("the fixed CAN ID and eight-byte frame are valid");
        socket
            .write_frame(&frame)
            .context("write STM32 CAN command frame")?;
        sequence = sequence.wrapping_add(1);
        thread::sleep(interval);
    }
}

fn env_number<T: std::str::FromStr>(name: &str, default: T) -> Result<T>
where
    T::Err: std::error::Error + Send + Sync + 'static,
{
    match env::var(name) {
        Ok(value) => value
            .parse()
            .with_context(|| format!("{name} has an invalid value")),
        Err(_) => Ok(default),
    }
}
