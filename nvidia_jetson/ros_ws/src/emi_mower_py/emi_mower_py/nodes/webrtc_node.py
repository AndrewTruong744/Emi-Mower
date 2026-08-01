import asyncio
import json
import logging
import threading

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image

import zenoh
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer


class WebRTCNode(Node):
    def __init__(self):
        super().__init__('webrtc_node')

        # Parameters
        self.declare_parameter('camera_topic', '/oak/rgb/image_raw')
        self.declare_parameter('mower_id', 'mower-01')

        self.camera_topic = self.get_parameter('camera_topic').value
        self.mower_id = self.get_parameter('mower_id').value

        # Zenoh Session (Inherits mTLS config from ZENOH_SESSION_CONFIG_URI)
        self.get_logger().info("Opening Zenoh session for WebRTC signaling...")
        self.zenoh_session = zenoh.open()

        # Key expression for signaling this specific mower
        self.signaling_key = f"mowers/{self.mower_id}/webrtc/offer"

        # ROS 2 Subscriptions
        self.subscription = self.create_subscription(
            Image,
            self.camera_topic,
            self.image_callback,
            10
        )

        self.pc = None
        self.is_connected = False
        self.get_logger().info(f'WebRTC Node initialized. Signaling on Zenoh: {self.signaling_key}')

    def image_callback(self, msg: Image):
        # Store frame or feed custom VideoStreamTrack
        pass

    async def start_webrtc_connection(self):
        """Creates WebRTC connection and sends SDP Offer over Zenoh RPC to the signaling backend."""
        backoff_delay = 2.0
        max_delay = 30.0

        while rclpy.ok():
            try:
                self.get_logger().info("Initializing new WebRTC PeerConnection...")

                config = RTCConfiguration(
                    iceServers=[RTCIceServer(urls=["stun:stun.cloudflare.com:3478"])]
                )
                self.pc = RTCPeerConnection(configuration=config)

                @self.pc.on("connectionstatechange")
                async def on_connectionstatechange():
                    self.get_logger().info(f"ICE Connection State: {self.pc.connectionState}")
                    if self.pc.connectionState in ["failed", "closed", "disconnected"]:
                        self.is_connected = False

                # 1. Generate local SDP Offer
                offer = await self.pc.createOffer()
                await self.pc.setLocalDescription(offer)

                # Prepare SDP payload
                offer_payload = json.dumps({
                    "sdp": self.pc.localDescription.sdp,
                    "type": self.pc.localDescription.type
                }).encode('utf-8')

                self.get_logger().info("Sending SDP Offer via Zenoh Query...")

                # 2. Send SDP Offer over Zenoh RPC (get queryable response)
                # This queries your backend service handling 'mowers/mower-01/webrtc/offer'
                replies = self.zenoh_session.get(
                    self.signaling_key,
                    payload=offer_payload,
                    target=zenoh.QueryTarget.BEST_MATCHING()
                )

                answer_data = None
                for reply in replies:
                    if reply.ok:
                        answer_data = json.loads(reply.ok.payload.to_string())
                        break
                    elif reply.err:
                        self.get_logger().error(f"Zenoh RPC Error: {reply.err.payload.to_string()}")

                if answer_data and "sdp" in answer_data:
                    # 3. Apply Remote SDP Answer returned over Zenoh
                    answer = RTCSessionDescription(
                        sdp=answer_data["sdp"],
                        type=answer_data["type"]
                    )
                    await self.pc.setRemoteDescription(answer)

                    self.get_logger().info("✅ WebRTC Session established via Zenoh signaling!")
                    self.is_connected = True
                    backoff_delay = 2.0

                    # Keep connection alive while monitoring state
                    while self.is_connected and rclpy.ok():
                        await asyncio.sleep(2.0)
                else:
                    self.get_logger().warning("No valid SDP Answer received from Zenoh queryable.")

            except Exception as e:
                self.get_logger().error(f"Unexpected WebRTC/Zenoh signaling error: {e}")

            # Cleanup PeerConnection before retry
            if self.pc:
                await self.pc.close()
                self.pc = None

            self.is_connected = False
            self.get_logger().info(f"Retrying WebRTC signaling in {backoff_delay}s...")
            await asyncio.sleep(backoff_delay)
            backoff_delay = min(backoff_delay * 1.5, max_delay)

    def destroy_node(self):
        if hasattr(self, 'zenoh_session') and self.zenoh_session:
            self.zenoh_session.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = WebRTCNode()

    # Run ROS 2 executor in background daemon thread
    ros_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    ros_thread.start()

    # Run asyncio event loop for WebRTC and Zenoh async processing
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(node.start_webrtc_connection())
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()