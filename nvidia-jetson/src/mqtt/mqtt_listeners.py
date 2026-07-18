import json
from std_msgs.msg import String

class MqttCloudListeners:
    """
    Handles converting incoming cloud MQTT data streams into 
    dedicated, target-injected native ROS 2 messages.
    """
    def setup_ros_publishers(self):
        """
        Creates the explicit ROS publisher injection channels.
        'self' will cleanly attach to the main CleanMqttNode at runtime.
        """
        # Channel A: Injects high-level operations commands (STOP, START, DOCK)
        self.cmd_pub = self.create_publisher(
            String, 
            '/mower/system_commands', 
            10
        )
        
        # Channel B: Injects remote WebRTC connection offers from the cloud dashboard
        self.webrtc_offer_pub = self.create_publisher(
            String, 
            '/mower/webrtc/remote_offer', 
            10
        )
        
        self.get_logger().info("Egress ROS 2 injection channels successfully allocated.")

    async def listen_mqtt(self, client):
        """Listens for inbound cloud payloads and injects them into the correct ROS channel."""
        async for message in client.messages:
            topic = str(message.topic)
            
            try:
                payload = message.payload.decode('utf-8')
            except Exception as e:
                self.get_logger().error(f"Failed to decode inbound network payload: {e}")
                continue

            self.get_logger().info(f"MQTT Inbound Match -> Topic Header: {topic}")

            # Prepare the standard ROS message structure
            ros_msg = String(data=payload)

            # ------------------------------------------------------------------
            # INJECTION ROUTING LOOP
            # Inspect the incoming MQTT topic header string and choose the target
            # ROS publisher object to execute the internal hardware injection.
            # ------------------------------------------------------------------
            if "/video/offer" in topic:
                # Inject directly into the standalone WebRTC streaming node's channel
                self.webrtc_offer_pub.publish(ros_msg)
                self.get_logger().info("Injected remote WebRTC offer into /mower/webrtc/remote_offer")
                
            elif "/commands" in topic:
                # Inject directly into the core VLA/state-machine execution channel
                self.cmd_pub.publish(ros_msg)
                self.get_logger().info("Injected system instruction into /mower/system_commands")