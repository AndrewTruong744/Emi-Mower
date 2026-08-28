//! Forward the real control topic to MuJoCo's command input without serial I/O.

use anyhow::{Context, Result};
use geometry_msgs::msg::TwistStamped;
use rclrs::{Context as RosContext, CreateBasicExecutor, RclrsErrorFilter, SpinOptions};

fn main() -> Result<()> {
    let ros_context = RosContext::default_from_env().context("initialize ROS context")?;
    let mut executor = ros_context.create_basic_executor();
    let node = executor
        .create_node("sim_command_sink")
        .context("create simulator command sink")?;
    let publisher = node
        .create_publisher::<TwistStamped>("/sim/cmd_vel")
        .context("create /sim/cmd_vel publisher")?;
    let _subscription = node
        .create_subscription("/teleop/cmd_vel", move |message: TwistStamped| {
            if let Err(error) = publisher.publish(message) {
                eprintln!("failed to publish /sim/cmd_vel: {error}");
            }
        })
        .context("subscribe to /teleop/cmd_vel")?;

    executor.spin(SpinOptions::default()).first_error()?;
    Ok(())
}
