import asyncio
from std_msgs.msg import String

class MowerRosSubscribers:
    """
    A Mixin class that handles all ROS 2 subscriptions and routing callbacks.
    This will be mixed directly into our main MQTT node.
    """
    def setup_ros_subscriptions(self):
        # We define the subscriptions here. 
        # Note: 'self' will eventually refer to your main CleanMqttNode!
        
        self.sdp_offer_sub = self.create_subscription(
            String,
            '/mower/webrtc/local_offer',
            self.ros_sdp_offer_callback,
            10
        )
        
        self.telemetry_sub = self.create_subscription(
            String,
            '/mower/brain/telemetry',
            self.ros_telemetry_callback,
            10
        )
        self.get_logger().info("All ROS 2 subscriptions initialized successfully.")

    def ros_sdp_offer_callback(self, msg: String):
        """Intercepts internal WebRTC offers and tags them for the cloud."""
        target_mqtt_topic = f"/mower/{self.mower_uuid}/video/offer"
        packet = {"topic": target_mqtt_topic, "payload": msg.data}
        self._push_to_async_queue(packet)

    def ros_telemetry_callback(self, msg: String):
        """Intercepts raw status info and tags them for the tracking stream."""
        target_mqtt_topic = f"/mower/{self.mower_uuid}/telemetry/data"
        packet = {"topic": target_mqtt_topic, "payload": msg.data}
        self._push_to_async_queue(packet)

    def _push_to_async_queue(self, packet: dict):
        """Helper method to thread-safely drop packages into the async queue."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.call_soon_threadsafe(self.outbound_queue.put_nowait, packet)