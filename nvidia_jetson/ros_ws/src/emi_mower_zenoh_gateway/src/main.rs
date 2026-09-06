//! Own the native Zenoh routes at the app/backend boundary.

use anyhow::{Context, Result};
use emi_mower_interfaces::msg::TelemetryBatch;
use emi_mower_zenoh_gateway::generated::zenoh_paths::{mower_joystick_path, mower_telemetry_path};
use emi_mower_zenoh_gateway::renewal::renew_certificate_if_needed;
use emi_mower_zenoh_gateway::{
    joystick_to_velocity, parse_joystick_payload, telemetry_payload, validate_mower_id,
    RosImuTelemetry, RosTelemetryRecord, TELEMETRY_TOPIC, TELEOP_TOPIC,
};
use geometry_msgs::msg::TwistStamped;
use rclrs::{Context as RosContext, CreateBasicExecutor, RclrsErrorFilter, SpinOptions};
use std::env;
use std::time::Duration;
use tokio::sync::mpsc;
use zenoh::config::Config;

const INITIAL_RETRY: Duration = Duration::from_secs(2);
const MAX_RETRY: Duration = Duration::from_secs(30);

#[tokio::main]
async fn main() -> Result<()> {
    let mower_id =
        env::var("MOWER_ID").context("set MOWER_ID in the provisioned Jetson environment")?;
    let max_linear_mps = env_number("MAX_LINEAR_MPS", 1.0)?;
    let max_angular_radps = env_number("MAX_ANGULAR_RADPS", 1.0)?;
    if !max_linear_mps.is_finite()
        || !max_angular_radps.is_finite()
        || max_linear_mps <= 0.0
        || max_angular_radps <= 0.0
    {
        anyhow::bail!("MAX_LINEAR_MPS and MAX_ANGULAR_RADPS must be finite positive values");
    }
    validate_mower_id(&mower_id)?;
    match renew_certificate_if_needed(&mower_id).await {
        Ok(true) => eprintln!("renewed mower operational certificate; opening main mTLS session"),
        Ok(false) => {}
        Err(error) => eprintln!("certificate renewal was unavailable: {error}"),
    }
    let joystick_key = mower_joystick_path(&mower_id);
    let telemetry_key = mower_telemetry_path(&mower_id);
    let (telemetry_tx, telemetry_rx) = mpsc::channel(8);

    let ros_context = RosContext::default_from_env().context("initialize ROS context")?;
    let mut executor = ros_context.create_basic_executor();
    let node = executor
        .create_node("zenoh_gateway")
        .context("create Zenoh gateway ROS node")?;
    let velocity_publisher = node
        .create_publisher::<TwistStamped>(TELEOP_TOPIC)
        .context("create /teleop/cmd_vel publisher")?;
    let telemetry_mower_id = mower_id.clone();
    let _telemetry_subscription =
        node.create_subscription(TELEMETRY_TOPIC, move |batch: TelemetryBatch| {
            match telemetry_payload(&telemetry_mower_id, &telemetry_records(&batch)) {
                Ok(payload) => {
                    if telemetry_tx.try_send(payload).is_err() {
                        eprintln!("dropping telemetry: gateway queue is full or closed");
                    }
                }
                Err(error) => eprintln!("rejected ROS telemetry: {error}"),
            }
        })
        .context("subscribe to /mower/telemetry")?;

    std::thread::spawn(move || {
        if let Err(error) = executor.spin(SpinOptions::default()).first_error() {
            eprintln!("Zenoh gateway ROS executor stopped: {error}");
        }
    });

    run_gateway(
        &joystick_key,
        &telemetry_key,
        max_linear_mps,
        max_angular_radps,
        velocity_publisher,
        telemetry_rx,
    )
    .await
}

async fn run_gateway(
    joystick_key: &str,
    telemetry_key: &str,
    max_linear_mps: f64,
    max_angular_radps: f64,
    velocity_publisher: rclrs::Publisher<TwistStamped>,
    mut telemetry_rx: mpsc::Receiver<Vec<u8>>,
) -> Result<()> {
    let config_path = env::var("ZENOH_CONFIG")
        .or_else(|_| env::var("ZENOH_SESSION_CONFIG_URI"))
        .context("set ZENOH_CONFIG or ZENOH_SESSION_CONFIG_URI")?;
    let mut retry_delay = INITIAL_RETRY;

    loop {
        let config = match Config::from_file(&config_path) {
            Ok(config) => config,
            Err(error) => {
                eprintln!("Zenoh gateway could not load config {config_path}: {error}");
                retry_delay = wait_to_retry(retry_delay).await;
                continue;
            }
        };
        let session = match zenoh::open(config).await {
            Ok(session) => session,
            Err(error) => {
                eprintln!("Zenoh gateway could not connect to router: {error}");
                retry_delay = wait_to_retry(retry_delay).await;
                continue;
            }
        };
        let subscriber = match session.declare_subscriber(joystick_key).await {
            Ok(subscriber) => subscriber,
            Err(error) => {
                eprintln!("Zenoh gateway could not subscribe to {joystick_key}: {error}");
                let _ = session.close().await;
                retry_delay = wait_to_retry(retry_delay).await;
                continue;
            }
        };

        eprintln!("Zenoh gateway connected; joystick={joystick_key}, telemetry={telemetry_key}");
        retry_delay = INITIAL_RETRY;
        loop {
            tokio::select! {
                sample = subscriber.recv_async() => match sample {
                    Ok(sample) => {
                        let payload = sample.payload().to_bytes();
                        match parse_joystick_payload(payload.as_ref()) {
                            Ok(joystick) => {
                                let (linear_mps, angular_radps) = joystick_to_velocity(
                                    joystick, max_linear_mps, max_angular_radps,
                                );
                                let mut message = TwistStamped::default();
                                message.twist.linear.x = linear_mps;
                                message.twist.angular.z = angular_radps;
                                if let Err(error) = velocity_publisher.publish(message) {
                                    eprintln!("failed to publish {TELEOP_TOPIC}: {error}");
                                }
                            }
                            Err(error) => eprintln!("rejected joystick command on {joystick_key}: {error}"),
                        }
                    }
                    Err(error) => {
                        eprintln!("Zenoh joystick subscription ended: {error}");
                        break;
                    }
                },
                payload = telemetry_rx.recv() => match payload {
                    Some(payload) => {
                        if let Err(error) = session.put(telemetry_key, payload).await {
                            eprintln!("failed to publish telemetry on {telemetry_key}: {error}");
                        }
                    }
                    None => return Ok(()),
                },
            }
        }
        let _ = session.close().await;
        retry_delay = wait_to_retry(retry_delay).await;
    }
}

async fn wait_to_retry(retry_delay: Duration) -> Duration {
    eprintln!("retrying Zenoh connection in {}s", retry_delay.as_secs());
    tokio::time::sleep(retry_delay).await;
    std::cmp::min(retry_delay.saturating_mul(2), MAX_RETRY)
}

fn telemetry_records(batch: &TelemetryBatch) -> Vec<RosTelemetryRecord> {
    batch
        .records
        .iter()
        .map(|record| RosTelemetryRecord {
            timestamp_seconds: i64::from(record.header.stamp.sec),
            timestamp_nanoseconds: record.header.stamp.nanosec,
            latitude: record.latitude,
            longitude: record.longitude,
            battery_percentage: record.battery_percentage,
            left_motor_speed: record.left_motor_speed,
            left_motor_direction: record.left_motor_direction,
            right_motor_speed: record.right_motor_speed,
            right_motor_direction: record.right_motor_direction,
            cutting_motor_speed: record.cutting_motor_speed,
            slippage_detected: record.slippage_detected,
            imu_data: record.has_imu_data.then(|| RosImuTelemetry {
                accel_x: record.accel_x,
                accel_y: record.accel_y,
                accel_z: record.accel_z,
                gyro_x: record.gyro_x,
                gyro_y: record.gyro_y,
                gyro_z: record.gyro_z,
                mag_x: record.mag_x,
                mag_y: record.mag_y,
                mag_z: record.mag_z,
            }),
        })
        .collect()
}

fn env_number(name: &str, default: f64) -> Result<f64> {
    match env::var(name) {
        Ok(value) => value
            .parse::<f64>()
            .with_context(|| format!("{name} must be a number")),
        Err(_) => Ok(default),
    }
}
