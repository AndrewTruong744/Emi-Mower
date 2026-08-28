//! Translate the app's native Zenoh joystick route into a ROS velocity topic.

use anyhow::{Context, Result};
use emi_mower_control::{joystick_key, joystick_to_velocity, parse_joystick_payload};
use geometry_msgs::msg::TwistStamped;
use rclrs::{Context as RosContext, CreateBasicExecutor, RclrsErrorFilter, SpinOptions};
use std::env;
use std::time::Duration;
use zenoh::config::Config;

#[tokio::main]
async fn main() -> Result<()> {
    let mower_id = env::var("MOWER_ID").unwrap_or_else(|_| "mower-01".to_owned());
    let max_linear_mps = env_number("MAX_LINEAR_MPS", 1.0)?;
    let max_angular_radps = env_number("MAX_ANGULAR_RADPS", 1.0)?;
    if !max_linear_mps.is_finite()
        || !max_angular_radps.is_finite()
        || max_linear_mps <= 0.0
        || max_angular_radps <= 0.0
    {
        anyhow::bail!("MAX_LINEAR_MPS and MAX_ANGULAR_RADPS must be finite positive values");
    }
    let key = joystick_key(&mower_id)?;

    let ros_context = RosContext::default_from_env().context("initialize ROS context")?;
    let mut executor = ros_context.create_basic_executor();
    let node = executor
        .create_node("teleop_gateway")
        .context("create teleop gateway ROS node")?;
    let publisher = node
        .create_publisher::<TwistStamped>("/teleop/cmd_vel")
        .context("create /teleop/cmd_vel publisher")?;

    std::thread::spawn(move || {
        if let Err(error) = executor.spin(SpinOptions::default()).first_error() {
            eprintln!("teleop gateway ROS executor stopped: {error}");
        }
    });

    let config_path = env::var("ZENOH_CONFIG")
        .or_else(|_| env::var("ZENOH_SESSION_CONFIG_URI"))
        .context("set ZENOH_CONFIG or ZENOH_SESSION_CONFIG_URI")?;
    let initial_retry = Duration::from_secs(2);
    let mut retry_delay = initial_retry;
    loop {
        let config = match Config::from_file(&config_path) {
            Ok(config) => config,
            Err(error) => {
                eprintln!("teleop gateway could not load Zenoh config {config_path}: {error}");
                tokio::time::sleep(retry_delay).await;
                retry_delay = std::cmp::min(retry_delay.saturating_mul(2), Duration::from_secs(30));
                continue;
            }
        };
        match zenoh::open(config).await {
            Ok(session) => match session.declare_subscriber(&key).await {
                Ok(subscriber) => {
                    eprintln!("teleop gateway connected; listening on {key}");
                    retry_delay = initial_retry;
                    while let Ok(sample) = subscriber.recv_async().await {
                        let payload = sample.payload().to_bytes();
                        match parse_joystick_payload(payload.as_ref()) {
                            Ok(joystick) => {
                                let velocity = joystick_to_velocity(
                                    joystick,
                                    max_linear_mps,
                                    max_angular_radps,
                                );
                                let mut message = TwistStamped::default();
                                message.twist.linear.x = velocity.linear_mps;
                                message.twist.angular.z = velocity.angular_radps;
                                if let Err(error) = publisher.publish(message) {
                                    eprintln!("failed to publish /teleop/cmd_vel: {error}");
                                }
                            }
                            Err(error) => eprintln!("rejected joystick command on {key}: {error}"),
                        }
                    }
                    eprintln!("teleop gateway Zenoh subscription ended; reconnecting");
                    if let Err(error) = session.close().await {
                        eprintln!("failed to close Zenoh session: {error}");
                    }
                }
                Err(error) => {
                    eprintln!("teleop gateway could not subscribe to {key}: {error}");
                    if let Err(close_error) = session.close().await {
                        eprintln!("failed to close Zenoh session: {close_error}");
                    }
                }
            },
            Err(error) => eprintln!("teleop gateway could not connect to Zenoh: {error}"),
        }

        eprintln!("retrying Zenoh connection in {}s", retry_delay.as_secs());
        tokio::time::sleep(retry_delay).await;
        retry_delay = std::cmp::min(retry_delay.saturating_mul(2), Duration::from_secs(30));
    }
}

fn env_number(name: &str, default: f64) -> Result<f64> {
    match env::var(name) {
        Ok(value) => value
            .parse::<f64>()
            .with_context(|| format!("{name} must be a number")),
        Err(_) => Ok(default),
    }
}
