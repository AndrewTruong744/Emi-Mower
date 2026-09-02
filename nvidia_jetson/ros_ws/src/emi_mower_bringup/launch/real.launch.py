"""Run the physical mower's camera, lidar, LiveKit, and STM32 CAN bridge."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import EnvironmentVariable, LaunchConfiguration
from launch_ros.actions import Node


def _zenoh_environment():
    default_config = os.path.join(
        get_package_share_directory("emi_mower_bringup"), "config", "zenoh_client.json5"
    )
    config = EnvironmentVariable("ZENOH_SESSION_CONFIG_URI", default_value=default_config)
    return [
        SetEnvironmentVariable(name="RMW_IMPLEMENTATION", value="rmw_zenoh_cpp"),
        SetEnvironmentVariable(name="ZENOH_SESSION_CONFIG_URI", value=config),
        SetEnvironmentVariable(
            name="ZENOH_CONFIG",
            value=EnvironmentVariable("ZENOH_CONFIG", default_value=config),
        ),
    ]


def generate_launch_description():
    mower_id = LaunchConfiguration("mower_id")
    can_interface = LaunchConfiguration("can_interface")

    sllidar_launch = os.path.join(
        get_package_share_directory("sllidar_ros2"), "launch", "sllidar_s2_launch.py"
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("mower_id", default_value="mower-01"),
            DeclareLaunchArgument(
                "can_interface",
                default_value=EnvironmentVariable(
                    "STM32_CAN_INTERFACE", default_value="can0"
                ),
            ),
            *_zenoh_environment(),
            SetEnvironmentVariable(name="MOWER_ID", value=mower_id),
            SetEnvironmentVariable(name="STM32_CAN_INTERFACE", value=can_interface),
            Node(
                package="depthai_ros_driver",
                executable="camera",
                name="oak",
                parameters=[{"rgb.i_set_focus": True, "rgb.i_focus": 0}],
                respawn=True,
                respawn_delay=2.0,
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(sllidar_launch),
                launch_arguments={
                    "serial_port": "/dev/rplidar",
                    "serial_baudrate": "1000000",
                    "frame_id": "laser_frame",
                }.items(),
            ),
            Node(
                package="emi_mower_livekit",
                executable="livekit_node",
                name="livekit_node",
                parameters=[{"mower_id": mower_id, "camera_topic": "/oak/rgb/image_raw"}],
                respawn=True,
                respawn_delay=2.0,
            ),
            Node(
                package="emi_mower_zenoh_gateway",
                executable="zenoh_gateway",
                name="zenoh_gateway",
                respawn=True,
                respawn_delay=2.0,
            ),
            Node(
                package="emi_mower_control",
                executable="stm32_bridge",
                name="stm32_bridge",
                respawn=True,
                respawn_delay=2.0,
            ),
        ]
    )
