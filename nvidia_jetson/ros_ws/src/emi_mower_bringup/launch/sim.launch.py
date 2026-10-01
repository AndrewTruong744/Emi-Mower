"""Run the app-to-ROS control path without physical sensors or CAN hardware."""

from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable
from launch.substitutions import EnvironmentVariable, LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    mower_id = LaunchConfiguration("mower_id")
    teleop_topic = ["/mower/", mower_id, "/teleop/cmd_vel"]
    sim_topic = ["/mower/", mower_id, "/sim/cmd_vel"]
    blade_topic = ["/mower/", mower_id, "/sim/blade_enable"]
    telemetry_topic = ["/mower/", mower_id, "/telemetry"]
    cutout_topic = ["/mower/", mower_id, "/boundary_cutout/download"]
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
                remappings=[
                    ("/teleop/cmd_vel", teleop_topic),
                    ("/mower/telemetry", telemetry_topic),
                    ("/mower/boundary_cutout/download", cutout_topic),
                ],
                respawn=True,
                respawn_delay=2.0,
            ),
            Node(
                package="emi_mower_boundary",
                executable="boundary_cutout_node",
                name="boundary_cutout_node",
                remappings=[("/mower/boundary_cutout/download", cutout_topic)],
                respawn=True,
                respawn_delay=2.0,
            ),
            Node(
                package="emi_mower_control",
                executable="sim_command_sink",
                name="sim_command_sink",
                parameters=[{"use_sim_time": True}],
                remappings=[("/teleop/cmd_vel", teleop_topic), ("/sim/cmd_vel", sim_topic)],
                respawn=True,
                respawn_delay=2.0,
            ),
            Node(
                package="emi_mower_bringup",
                executable="sim_bridge",
                name="sim_bridge",
                remappings=[("/sim/cmd_vel", sim_topic), ("/sim/blade_enable", blade_topic)],
                respawn=True,
                respawn_delay=2.0,
            ),
        ]
    )
