//! Own the native Zenoh routes at the app/backend boundary.

use anyhow::{Context, Result};
use emi_mower_interfaces::msg::{CutoutDownload, TelemetryBatch};
use emi_mower_zenoh_gateway::generated::zenoh_paths::{
    mower_cutout_delivery_path, mower_joystick_path, mower_liveliness_path, mower_telemetry_path,
};
use emi_mower_zenoh_gateway::renewal::renew_certificate_if_needed;
use emi_mower_zenoh_gateway::{
    joystick_to_velocity, parse_cutout_delivery, parse_joystick_payload, telemetry_payload,
    validate_mower_id, RosImuTelemetry, RosTelemetryRecord, CUTOUT_DOWNLOAD_TOPIC, TELEMETRY_TOPIC,
    TELEOP_TOPIC,
};
use geometry_msgs::msg::TwistStamped;
use rclrs::{Context as RosContext, CreateBasicExecutor, RclrsErrorFilter, SpinOptions};
use std::env;
use std::time::Duration;
use tokio::sync::mpsc;
use zenoh::config::Config;

const INITIAL_RETRY: Duration = Duration::from_secs(2);
const MAX_RETRY: Duration = Duration::from_secs(30);
const CERTIFICATE_RENEWAL_CHECK_PERIOD: Duration = Duration::from_secs(6 * 60 * 60);

struct GatewayKeys<'a> {
    joystick: &'a str,
    telemetry: &'a str,
    cutout_delivery: &'a str,
    liveliness: &'a str,
}

struct GatewaySettings {
    max_linear_mps: f64,
    max_angular_radps: f64,
}

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
    let cutout_delivery_key = mower_cutout_delivery_path(&mower_id);
    let liveliness_key = mower_liveliness_path(&mower_id);
    let (telemetry_tx, telemetry_rx) = mpsc::channel(8);

    let ros_context = RosContext::default_from_env().context("initialize ROS context")?;
    let mut executor = ros_context.create_basic_executor();
    let node = executor
        .create_node("zenoh_gateway")
        .context("create Zenoh gateway ROS node")?;
    let velocity_publisher = node
        .create_publisher::<TwistStamped>(TELEOP_TOPIC)
        .context("create /teleop/cmd_vel publisher")?;
    let cutout_download_publisher = node
        .create_publisher::<CutoutDownload>(CUTOUT_DOWNLOAD_TOPIC)
        .context("create boundary cutout download publisher")?;
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
        &mower_id,
        GatewayKeys {
            joystick: &joystick_key,
            telemetry: &telemetry_key,
            cutout_delivery: &cutout_delivery_key,
            liveliness: &liveliness_key,
        },
        GatewaySettings {
            max_linear_mps,
            max_angular_radps,
        },
        velocity_publisher,
        cutout_download_publisher,
        telemetry_rx,
    )
    .await
}

async fn run_gateway(
    mower_id: &str,
    keys: GatewayKeys<'_>,
    settings: GatewaySettings,
    velocity_publisher: rclrs::Publisher<TwistStamped>,
    cutout_download_publisher: rclrs::Publisher<CutoutDownload>,
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
        let subscriber = match session.declare_subscriber(keys.joystick).await {
            Ok(subscriber) => subscriber,
            Err(error) => {
                eprintln!(
                    "Zenoh gateway could not subscribe to {}: {error}",
                    keys.joystick
                );
                let _ = session.close().await;
                retry_delay = wait_to_retry(retry_delay).await;
                continue;
            }
        };
        let cutout_subscriber = match session.declare_subscriber(keys.cutout_delivery).await {
            Ok(subscriber) => subscriber,
            Err(error) => {
                eprintln!(
                    "Zenoh gateway could not subscribe to {}: {error}",
                    keys.cutout_delivery
                );
                let _ = session.close().await;
                retry_delay = wait_to_retry(retry_delay).await;
                continue;
            }
        };
        // The token exists only while this authenticated gateway session is
        // usable. Apps subscribe directly with history to see both its
        // declaration and deletion without a backend/Valkey status cache.
        let _liveliness_token = match session.liveliness().declare_token(keys.liveliness).await {
            Ok(token) => token,
            Err(error) => {
                eprintln!(
                    "Zenoh gateway could not declare liveliness token {}: {error}",
                    keys.liveliness
                );
                let _ = session.close().await;
                retry_delay = wait_to_retry(retry_delay).await;
                continue;
            }
        };

        eprintln!(
            "Zenoh gateway connected; joystick={}, telemetry={}, cutout={}, liveliness={}",
            keys.joystick, keys.telemetry, keys.cutout_delivery, keys.liveliness,
        );
        retry_delay = INITIAL_RETRY;
        let mut certificate_renewal_check = tokio::time::interval_at(
            tokio::time::Instant::now() + CERTIFICATE_RENEWAL_CHECK_PERIOD,
            CERTIFICATE_RENEWAL_CHECK_PERIOD,
        );
        certificate_renewal_check.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Skip);
        loop {
            tokio::select! {
                sample = subscriber.recv_async() => match sample {
                    Ok(sample) => {
                        let payload = sample.payload().to_bytes();
                        match parse_joystick_payload(payload.as_ref()) {
                            Ok(joystick) => {
                                let (linear_mps, angular_radps) = joystick_to_velocity(
                                    joystick, settings.max_linear_mps, settings.max_angular_radps,
                                );
                                let mut message = TwistStamped::default();
                                message.twist.linear.x = linear_mps;
                                message.twist.angular.z = angular_radps;
                                if let Err(error) = velocity_publisher.publish(message) {
                                    eprintln!("failed to publish {TELEOP_TOPIC}: {error}");
                                }
                            }
                            Err(error) => eprintln!("rejected joystick command on {}: {error}", keys.joystick),
                        }
                    }
                    Err(error) => {
                        eprintln!("Zenoh joystick subscription ended: {error}");
                        break;
                    }
                },
                payload = telemetry_rx.recv() => match payload {
                    Some(payload) => {
                        if let Err(error) = session.put(keys.telemetry, payload).await {
                            eprintln!("failed to publish telemetry on {}: {error}", keys.telemetry);
                        }
                    }
                    None => return Ok(()),
                },
                sample = cutout_subscriber.recv_async() => match sample {
                    Ok(sample) => match parse_cutout_delivery(sample.payload().to_bytes().as_ref()) {
                        Ok(response) => {
                        let message = CutoutDownload {
                            cutout_id: response.cutout_id,
                            download_url: response.download_url,
                            expires_in: response.expires_in,
                            content_type: response.content_type,
                        };
                        if let Err(error) = cutout_download_publisher.publish(message) {
                            eprintln!("failed to publish {CUTOUT_DOWNLOAD_TOPIC}: {error}");
                        }
                    }
                        Err(error) => eprintln!("rejected cutout delivery on {}: {error}", keys.cutout_delivery),
                    },
                    Err(error) => { eprintln!("Zenoh cutout subscription ended: {error}"); break; }
                },
                _ = certificate_renewal_check.tick() => {
                    match renew_certificate_if_needed(mower_id).await {
                        Ok(true) => {
                            eprintln!("renewed mower operational certificate; reconnecting mTLS session");
                            break;
                        }
                        Ok(false) => {}
                        Err(error) => eprintln!("certificate renewal was unavailable: {error}"),
                    }
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
            imu_data: record.has_imu_data.then_some(RosImuTelemetry {
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
