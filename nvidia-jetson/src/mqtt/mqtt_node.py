import asyncio
import os
import ssl
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import rasyncio
import aiomqtt

from .ros_subscribers import MowerRosSubscribers
from .mqtt_listeners import MqttCloudListeners

class CleanMqttNode(Node, MowerRosSubscribers, MqttCloudListeners):
    def __init__(self):
        super().__init__('mqtt_bridge_node')
        
        # 1. Fetch parameters
        # Make sure to update paths
        self.declare_parameter('broker_host', '192.168.1.50')
        self.declare_parameter('broker_port', 8883)
        self.declare_parameter('cert_dir', '/etc/robot/certs')
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
        
        # Hand off the primary network thread tasks to rasyncio
        rasyncio.create_task(self.mqtt_network_loop())

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
                    
                    # Track subscriptions
                    await client.subscribe("/mower/+/video/offer")
                    await client.subscribe("/mower/commands/#")
                    
                    # Concurrently run inbound listener and outbound sender
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
            payload_data = await self.outbound_queue.get()
            try:
                await client.publish("mower/telemetry/status", payload=payload_data, qos=1)
            except aiomqtt.MqttError as e:
                await self.outbound_queue.put(payload_data)  # Requeue on failure
                raise e
            finally:
                self.outbound_queue.task_done()


def main(args=None):
    rclpy.init(args=args)
    node = CleanMqttNode()
    
    # rasyncio handles the executor spinning entirely behind the scenes
    rasyncio.spin(node)
    
    node.destroy_node()
    rclpy.shutdown()