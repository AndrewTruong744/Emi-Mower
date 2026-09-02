"""Run the app-to-ROS control path without physical sensors or CAN hardware."""

from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable
from launch.substitutions import EnvironmentVariable, LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    mower_id = LaunchConfiguration("mower_id")
    default_config = str(Path(__file__).parents[1] / "config" / "zenoh_client.json5")
    config = EnvironmentVariable("ZENOH_SESSION_CONFIG_URI", default_value=default_config)

    return LaunchDescription(
        [
            DeclareLaunchArgument("mower_id", default_value="mower-01"),
            SetEnvironmentVariable(name="RMW_IMPLEMENTATION", value="rmw_zenoh_cpp"),
            SetEnvironmentVariable(name="ZENOH_SESSION_CONFIG_URI", value=config),
            SetEnvironmentVariable(
                name="ZENOH_CONFIG",
                value=EnvironmentVariable("ZENOH_CONFIG", default_value=config),
            ),
            SetEnvironmentVariable(name="MOWER_ID", value=mower_id),
            SetEnvironmentVariable(name="ROS_USE_SIM_TIME", value="true"),
            Node(
                package="emi_mower_zenoh_gateway",
                executable="zenoh_gateway",
                name="zenoh_gateway",
                respawn=True,
                respawn_delay=2.0,
            ),
            Node(
                package="emi_mower_control",
                executable="sim_command_sink",
                name="sim_command_sink",
                parameters=[{"use_sim_time": True}],
                respawn=True,
                respawn_delay=2.0,
            ),
        ]
    )
