# ros_ws/src/my_project_bringup/launch/system.launch.py
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

def generate_launch_description():
    # 1. OAK-D S2 Node
    oakd_node = Node(
        package='depthai_ros_driver',
        executable='camera',
        name='oak',
        parameters=[{
            'rgb.i_set_focus': True,
            'rgb.i_focus': 0,  # 0 corresponds to Infinity Focus
        }]
    )

    # 2. Slamtec RPLIDAR S2 Node
    sllidar_launch_path = os.path.join(
        get_package_share_directory('sllidar_ros2'),
        'launch',
        'sllidar_s2_launch.py'
    )
    
    sllidar_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(sllidar_launch_path),
        launch_arguments={
            'serial_port': '/dev/rplidar', # or /dev/ttyUSB0
            'serial_baudrate': '1000000',  # S2 default baudrate
            'frame_id': 'laser_frame'
        }.items()
    )

    zenoh_config_path = os.path.join(
        get_package_share_directory('my_project_bringup'),
        'config',
        'zenoh_client.json5'
    )

    # Common Zenoh environment variables for all nodes
    zenoh_env = {
        'RMW_IMPLEMENTATION': 'rmw_zenoh_cpp',
        'ZENOH_SESSION_CONFIG_URI': zenoh_config_path
    }

    return LaunchDescription([
        oakd_node,
        sllidar_node
    ])