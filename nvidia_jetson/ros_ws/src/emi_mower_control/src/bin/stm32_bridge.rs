//! Convert safe ROS velocity commands into the STM32's Embassy UART protocol.

use anyhow::{Context, Result};
use emi_mower_control::{CommandWatchdog, Stm32CommandFrame, VelocityCommand};
use geometry_msgs::msg::TwistStamped;
use rclrs::{Context as RosContext, CreateBasicExecutor, RclrsErrorFilter, SpinOptions};
use std::env;
use std::io::Write;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};

fn main() -> Result<()> {
    let device = env::var("STM32_UART_DEVICE").unwrap_or_else(|_| "/dev/ttyTHS1".to_owned());
    let baud_rate = env_number("STM32_UART_BAUD", 115_200_u32)?;
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

    let uart_state = Arc::clone(&state);
    thread::spawn(move || {
        if let Err(error) = write_uart_frames(&device, baud_rate, uart_state) {
            eprintln!("STM32 UART bridge stopped: {error:#}");
        }
    });

    executor.spin(SpinOptions::default()).first_error()?;
    Ok(())
}

fn write_uart_frames(
    device: &str,
    baud_rate: u32,
    state: Arc<Mutex<CommandWatchdog>>,
) -> Result<()> {
    let mut port = serialport::new(device, baud_rate)
        .timeout(Duration::from_millis(20))
        .open()
        .with_context(|| format!("open STM32 UART {device} at {baud_rate} baud"))?;
    let mut sequence = 0_u32;
    let interval = Duration::from_millis(20);

    loop {
        let command = state
            .lock()
            .map(|watchdog| watchdog.command_at(Instant::now()))
            .unwrap_or(VelocityCommand::ZERO);
        let enabled = command != VelocityCommand::ZERO;
        let frame = Stm32CommandFrame::from_velocity(sequence, enabled, command).encode();
        port.write_all(&frame).context("write STM32 command frame")?;
        port.flush().context("flush STM32 UART")?;
        sequence = sequence.wrapping_add(1);
        thread::sleep(interval);
    }
}

fn env_number<T: std::str::FromStr>(name: &str, default: T) -> Result<T>
where
    T::Err: std::error::Error + Send + Sync + 'static,
{
    match env::var(name) {
        Ok(value) => value.parse().with_context(|| format!("{name} has an invalid value")),
        Err(_) => Ok(default),
    }
}
