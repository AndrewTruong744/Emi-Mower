#!/usr/bin/env python3
import asyncio
import os
import ssl
import threading
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import aiomqtt

# Internal module imports from your package
from nvidia_jetson_package.ros_subscribers import MowerRosSubscribers
from nvidia_jetson_package.mqtt_listeners import MqttCloudListeners

class CleanMqttNode(Node, MowerRosSubscribers, MqttCloudListeners):
    def __init__(self, main_loop):
        super().__init__('mqtt_bridge_node')
        self.main_loop = main_loop
        
        # 1. Fetch parameters
        self.declare_parameter('broker_host', '192.168.1.50')
        self.declare_parameter('broker_port', 8883)
        self.declare_parameter('cert_dir', '/home/andrewt/Repos/Emi-Mower/nvidia_jetson/certs')
        self.declare_parameter('mower_uuid', 'default_mower_uuid')
        
        self.broker_host = self.get_parameter('broker_host').value
        self.broker_port = self.get_parameter('broker_port').value
        cert_dir = self.get_parameter('cert_dir').value
        
        # 2. Configure mTLS paths
        self.ca_path = os.path.join(cert_dir, 'ca.crt')
        self.client_crt = os.path.join(cert_dir, 'mower.crt')
        self.client_key = os.path.join(cert_dir, 'mower.key')
        
        # 3. Pipelines & Thread-Safe Outbound Queue
        self.outbound_queue = asyncio.Queue()
        self.mower_uuid = self.get_parameter('mower_uuid').value

        self.setup_ros_subscriptions()
        self.setup_ros_publishers()

    def get_ssl_context(self) -> ssl.SSLContext | None:
        """Loads keys for mutual authentication verification."""
        try:
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=self.ca_path)
            context.load_cert_chain(certfile=self.client_crt, keyfile=self.client_key)
            return context
        except Exception as e:
            self.get_logger().error(f"Failed to load mTLS Context: {e}")
            return None

    async def mqtt_network_loop(self):
        """Self-healing connection manager."""
        ssl_context = self.get_ssl_context()
        if not ssl_context:
            return

        while rclpy.ok():
            try:
                self.get_logger().info(f"Connecting to broker at {self.broker_host}:{self.broker_port}...")
                async with aiomqtt.Client(
                    hostname=self.broker_host,
                    port=self.broker_port,
                    tls_context=ssl_context
                ) as client:
                    self.get_logger().info("Connected via mTLS!")
                    
                    await client.subscribe("/mower/+/video/answer")
                    await client.subscribe("/mower/+/telemetry/command")
                    await client.subscribe("/mower/+/command")
                    
                    await asyncio.gather(
                        self.listen_mqtt(client),
                        self.publish_outbound(client)
                    )
            except aiomqtt.MqttError as e:
                self.get_logger().warn(f"Network dropout: {e}. Retrying in 5s...")
                await asyncio.sleep(5.0)

    async def publish_outbound(self, client):
        """Pushes local robot status data up to Cloud/Backend."""
        while rclpy.ok():
            data = await self.outbound_queue.get()
            try:
                target_mqtt_topic = data.get("topic")
                packet = data.get("payload")
                await client.publish(target_mqtt_topic, payload=packet, qos=1)
            except aiomqtt.MqttError as e:
                await self.outbound_queue.put(data)
                raise e
            finally:
                self.outbound_queue.task_done()


def main(args=None):
    rclpy.init(args=args)
    loop = asyncio.get_event_loop()
    node = CleanMqttNode(loop)
    
    # Spin ROS 2 in a background thread so asyncio isn't blocked
    ros_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    ros_thread.start()
    
    try:
        loop.run_until_complete(node.mqtt_network_loop())
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()