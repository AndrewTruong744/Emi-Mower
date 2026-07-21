from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # Automate booting up your self-healing MQTT client node
        Node(
            package='nvidia_jetson_package',
            executable='mqtt_node.py',
            name='mqtt_bridge_node',
            output='screen',
            parameters=[{
                'broker_host': '192.168.1.73',
                'broker_port': 8883,
                'mower_uuid': 'emi_mower_alpha'
            }]
        )
    ])