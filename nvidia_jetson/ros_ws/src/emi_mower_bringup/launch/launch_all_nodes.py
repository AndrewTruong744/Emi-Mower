import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    SetEnvironmentVariable,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    mower_id = LaunchConfiguration("mower_id")
    camera_topic = LaunchConfiguration("camera_topic")

    # The depthai-ros driver publishes the OAK-D S2 RGB stream here by default.
    oakd_node = Node(
        package="depthai_ros_driver",
        executable="camera",
        name="oak",
        parameters=[
            {
                "rgb.i_set_focus": True,
                "rgb.i_focus": 0,
            }
        ],
    )

    # Slamtec RPLIDAR S2 Node
    sllidar_launch_path = os.path.join(
        get_package_share_directory("sllidar_ros2"),
        "launch",
        "sllidar_s2_launch.py",
    )

    sllidar_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(sllidar_launch_path),
        launch_arguments={
            "serial_port": "/dev/rplidar",
            "serial_baudrate": "1000000",
            "frame_id": "laser_frame",
        }.items(),
    )

    zenoh_config_path = os.path.join(
        get_package_share_directory("emi_mower_bringup"),
        "config",
        "zenoh_client.json5",
    )

    livekit_node = Node(
        package="emi_mower_py",
        executable="livekit_node",
        name="livekit_node",
        parameters=[
            {
                "mower_id": mower_id,
                "camera_topic": camera_topic,
            }
        ],
    )

    return LaunchDescription([
        DeclareLaunchArgument("mower_id", default_value="mower-01"),
        DeclareLaunchArgument(
            "camera_topic",
            default_value="/oak/rgb/image_raw",
            description="OAK-D S2 RGB image topic published by depthai-ros",
        ),
        SetEnvironmentVariable(
            name="RMW_IMPLEMENTATION",
            value="rmw_zenoh_cpp",
        ),
        SetEnvironmentVariable(
            name="ZENOH_SESSION_CONFIG_URI",
            value=zenoh_config_path,
        ),
        # Zenoh-Python uses ZENOH_CONFIG while rmw_zenoh_cpp uses
        # ZENOH_SESSION_CONFIG_URI.  Both must load the same mTLS session.
        SetEnvironmentVariable(
            name="ZENOH_CONFIG",
            value=zenoh_config_path,
        ),
        oakd_node,
        sllidar_node,
        livekit_node,
    ])
