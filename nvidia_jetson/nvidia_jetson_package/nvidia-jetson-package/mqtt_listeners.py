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
        # Injects high-level operations commands (STOP, START, DOCK)
        self.cmd_pub = self.create_publisher(
            String, 
            '/mower/system_commands', 
            10
        )

        self.cmd_telemetry_pub = self.create_publisher(
            String,
            '/mower/telemetry/command',
            10
        )
        
        # Injects remote WebRTC connection offers from the cloud dashboard
        self.webrtc_answer_pub = self.create_publisher(
            String, 
            '/mower/video/answer', 
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
            if "/video/answer" in topic:
                # Inject directly into the standalone WebRTC streaming node's channel
                self.webrtc_answer_pub.publish(ros_msg)
                self.get_logger().info("Injected remote WebRTC answer into /mower/video/answer")

            elif "/telemetry/command" in topic:
                # Inject directly into the core VLA/state-machine execution channel
                self.cmd_telemetry_pub.publish(ros_msg)
                self.get_logger().info("Injected telemetry command into /mower/telemetry/command")

            elif "/commands" in topic:
                # Inject directly into the core VLA/state-machine execution channel
                self.cmd_pub.publish(ros_msg)
                self.get_logger().info("Injected system instruction into /mower/system_commands")
