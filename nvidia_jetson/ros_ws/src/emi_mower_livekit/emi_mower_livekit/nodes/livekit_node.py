"""Publish the OAK-D RGB stream to the mower's LiveKit room."""

import asyncio
import json
import os
import threading
from dataclasses import dataclass

import numpy as np
import rclpy
from livekit import rtc
from rclpy.node import Node
from sensor_msgs.msg import Image

import zenoh


def _zenoh_config() -> zenoh.Config:
    """Load the same session config used by ``rmw_zenoh_cpp``.

    Zenoh-Python 1.9 requires a Config argument to ``open``.  The ROS
    middleware receives its config through ``ZENOH_SESSION_CONFIG_URI``;
    accepting that variable here keeps the Python session on the same router,
    TLS, and discovery settings as the ROS graph.  ``ZENOH_CONFIG`` is the
    native Zenoh-Python name and takes precedence when supplied explicitly.
    """
    config_path = os.environ.get("ZENOH_CONFIG") or os.environ.get(
        "ZENOH_SESSION_CONFIG_URI"
    )
    if config_path:
        return zenoh.Config.from_file(config_path)
    return zenoh.Config()


@dataclass(frozen=True)
class CameraFrame:
    """An RGB24 camera frame copied out of a ROS image message."""

    width: int
    height: int
    data: bytes
    timestamp_us: int


class LiveKitNode(Node):
    """Request a mower publisher token and publish the OAK-D RGB camera."""

    def __init__(self) -> None:
        super().__init__("livekit_node")

        self.declare_parameter("camera_topic", "/oak/rgb/image_raw")
        # The launch file normally passes this explicitly. Reading MOWER_ID as
        # the default also keeps direct ROS launches aligned with Docker .env.
        self.declare_parameter("mower_id", os.environ.get("MOWER_ID", "mower-01"))
        self.declare_parameter("video_fps", 15)
        self.declare_parameter("video_bitrate", 2_000_000)

        self.camera_topic = str(self.get_parameter("camera_topic").value)
        self.mower_id = str(self.get_parameter("mower_id").value)
        self.video_fps = int(self.get_parameter("video_fps").value)
        self.video_bitrate = int(self.get_parameter("video_bitrate").value)

        self.upload_key = f"mower/{self.mower_id}/livekit/upload"
        # Opening Zenoh may fail while the backend/router is still starting.
        # Keep ROS alive and let ``run`` reconnect with backoff instead.
        self.zenoh_session = None

        self._event_loop: asyncio.AbstractEventLoop | None = None
        self._frame_queue: asyncio.Queue[CameraFrame] | None = None
        self._livekit_room: rtc.Room | None = None
        self._video_source: rtc.VideoSource | None = None
        self._last_image_encoding: str | None = None

        self.subscription = self.create_subscription(
            Image,
            self.camera_topic,
            self.image_callback,
            1,
        )

        self.get_logger().info(
            f"LiveKit node initialized for {self.camera_topic}; "
            f"requesting tokens on Zenoh {self.upload_key}"
        )

    def attach_event_loop(self, event_loop: asyncio.AbstractEventLoop) -> None:
        """Attach the asyncio loop used by LiveKit and the camera queue."""
        self._event_loop = event_loop
        self._frame_queue = asyncio.Queue(maxsize=1)

    def image_callback(self, msg: Image) -> None:
        """Convert an OAK-D ROS image and enqueue only the newest frame."""
        try:
            frame = self._ros_image_to_rgb24(msg)
        except ValueError as error:
            encoding = str(msg.encoding).lower()
            if encoding != self._last_image_encoding:
                self.get_logger().error(
                    f"Cannot publish OAK-D image encoding {msg.encoding!r}: {error}"
                )
                self._last_image_encoding = encoding
            return

        if self._event_loop is None or self._frame_queue is None:
            return

        try:
            self._event_loop.call_soon_threadsafe(self._enqueue_frame, frame)
        except RuntimeError:
            # The asyncio loop is shutting down while ROS is still spinning.
            pass

    def _enqueue_frame(self, frame: CameraFrame) -> None:
        """Run on the asyncio loop and apply latest-frame backpressure."""
        if self._frame_queue is None:
            return

        if self._frame_queue.full():
            self._frame_queue.get_nowait()
        self._frame_queue.put_nowait(frame)

    @staticmethod
    def _ros_image_to_rgb24(msg: Image) -> CameraFrame:
        """Convert common ``sensor_msgs/Image`` encodings to packed RGB24."""
        width = int(msg.width)
        height = int(msg.height)
        encoding = str(msg.encoding).lower()
        if width <= 0 or height <= 0:
            raise ValueError("image dimensions must be positive")

        channels_by_encoding = {
            "rgb8": 3,
            "bgr8": 3,
            "rgba8": 4,
            "bgra8": 4,
            "mono8": 1,
        }
        channels = channels_by_encoding.get(encoding)
        if channels is None:
            raise ValueError("expected rgb8, bgr8, rgba8, bgra8, or mono8")

        row_step = int(msg.step) or width * channels
        raw = np.frombuffer(msg.data, dtype=np.uint8)
        required_bytes = row_step * height
        if raw.size < required_bytes:
            raise ValueError(
                f"image data is truncated ({raw.size} < {required_bytes} bytes)"
            )

        rows = raw[:required_bytes].reshape(height, row_step)
        pixels = rows[:, : width * channels].reshape(height, width, channels)

        if encoding == "rgb8":
            rgb = pixels
        elif encoding in ("bgr8", "bgra8"):
            rgb = pixels[..., [2, 1, 0]]
        elif encoding == "rgba8":
            rgb = pixels[..., :3]
        else:  # mono8
            rgb = np.repeat(pixels, 3, axis=2)

        stamp = msg.header.stamp
        timestamp_us = int(stamp.sec) * 1_000_000 + int(stamp.nanosec) // 1_000
        return CameraFrame(
            width=width,
            height=height,
            data=np.ascontiguousarray(rgb).tobytes(),
            timestamp_us=timestamp_us,
        )

    @staticmethod
    def _reply_payload(reply: object) -> bytes:
        """Read a Zenoh reply payload across supported Zenoh Python versions."""
        payload = reply.ok.payload  # type: ignore[attr-defined]
        if hasattr(payload, "to_bytes"):
            return payload.to_bytes()
        return bytes(payload)

    def _request_upload_token(self) -> dict[str, object]:
        """Request the publish-only LiveKit token from the backend queryable."""
        session = self._ensure_zenoh_session()
        replies = session.get(
            self.upload_key,
            payload=b"{}",
            target=zenoh.QueryTarget.BEST_MATCHING,
        )

        for reply in replies:
            if reply.ok:
                response = json.loads(self._reply_payload(reply).decode("utf-8"))
                if not response.get("token") or not response.get("url"):
                    raise RuntimeError("backend returned an invalid LiveKit token")
                return response
            if reply.err:
                error_payload = reply.err.payload
                if hasattr(error_payload, "to_string"):
                    error_text = error_payload.to_string()
                elif hasattr(error_payload, "to_bytes"):
                    error_text = error_payload.to_bytes().decode("utf-8")
                else:
                    error_text = str(error_payload)
                raise RuntimeError(f"LiveKit token request failed: {error_text}")

        raise RuntimeError("backend returned no LiveKit token reply")

    def _ensure_zenoh_session(self):
        """Open a Zenoh client only when a request is ready to be made."""
        if self.zenoh_session is None:
            self.get_logger().info("Connecting LiveKit node to Zenoh router")
            self.zenoh_session = zenoh.open(_zenoh_config())
        return self.zenoh_session

    def _reset_zenoh_session(self) -> None:
        """Discard a failed session so the next retry creates a fresh client."""
        if self.zenoh_session is not None:
            try:
                self.zenoh_session.close()
            finally:
                self.zenoh_session = None

    async def _next_frame(self, disconnected: asyncio.Event) -> CameraFrame:
        """Wait for a camera frame, or return when LiveKit disconnects."""
        if self._frame_queue is None:
            raise RuntimeError("camera queue is not initialized")

        frame_task = asyncio.create_task(self._frame_queue.get())
        disconnect_task = asyncio.create_task(disconnected.wait())
        done, pending = await asyncio.wait(
            (frame_task, disconnect_task),
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)

        if disconnect_task in done:
            raise RuntimeError("LiveKit room disconnected")
        return frame_task.result()

    async def _publish_camera(self, token_response: dict[str, object]) -> None:
        """Connect to LiveKit, publish a track, and feed it OAK-D frames."""
        room = rtc.Room(loop=asyncio.get_running_loop())
        disconnected = asyncio.Event()

        @room.on("disconnected")
        def on_disconnected(_reason: object) -> None:
            disconnected.set()

        self._livekit_room = room
        source: rtc.VideoSource | None = None
        try:
            await room.connect(str(token_response["url"]), str(token_response["token"]))
            self.get_logger().info(f"Connected to LiveKit room {room.name!r}")

            first_frame = await self._next_frame(disconnected)
            source = rtc.VideoSource(first_frame.width, first_frame.height)
            track = rtc.LocalVideoTrack.create_video_track("oak_rgb", source)
            publication = await room.local_participant.publish_track(
                track,
                rtc.TrackPublishOptions(
                    source=rtc.TrackSource.SOURCE_CAMERA,
                    video_encoding=rtc.VideoEncoding(
                        max_framerate=self.video_fps,
                        max_bitrate=self.video_bitrate,
                    ),
                ),
            )
            self._video_source = source
            self.get_logger().info(
                f"Published OAK-D RGB track {publication.sid} "
                f"({first_frame.width}x{first_frame.height})"
            )

            source.capture_frame(
                rtc.VideoFrame(
                    first_frame.width,
                    first_frame.height,
                    rtc.VideoBufferType.RGB24,
                    first_frame.data,
                ),
                timestamp_us=first_frame.timestamp_us,
            )

            while rclpy.ok() and room.isconnected():
                frame = await self._next_frame(disconnected)
                if (
                    frame.width != first_frame.width
                    or frame.height != first_frame.height
                ):
                    self.get_logger().warning(
                        "Ignoring OAK-D frame whose dimensions changed from "
                        f"{first_frame.width}x{first_frame.height} to "
                        f"{frame.width}x{frame.height}"
                    )
                    continue
                source.capture_frame(
                    rtc.VideoFrame(
                        frame.width,
                        frame.height,
                        rtc.VideoBufferType.RGB24,
                        frame.data,
                    ),
                    timestamp_us=frame.timestamp_us,
                )
        finally:
            self._video_source = None
            try:
                if room.isconnected():
                    await room.disconnect()
            finally:
                if source is not None:
                    await source.aclose()
                self._livekit_room = None

    async def run(self) -> None:
        """Keep requesting fresh tokens and reconnecting after failures."""
        retry_delay = 2.0
        while rclpy.ok():
            try:
                self.get_logger().info(
                    f"Requesting LiveKit upload token on {self.upload_key}"
                )
                token_response = await asyncio.to_thread(self._request_upload_token)
                await self._publish_camera(token_response)
                retry_delay = 2.0
            except asyncio.CancelledError:
                raise
            except Exception as error:
                self.get_logger().error(f"LiveKit upload error: {error}")
                self._reset_zenoh_session()

            if rclpy.ok():
                self.get_logger().info(f"Retrying LiveKit upload in {retry_delay:g}s")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 1.5, 30.0)

    def destroy_node(self) -> bool:
        self._reset_zenoh_session()
        return super().destroy_node()


async def _run_node(node: LiveKitNode) -> None:
    node.attach_event_loop(asyncio.get_running_loop())
    ros_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    ros_thread.start()
    await node.run()


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = LiveKitNode()
    try:
        asyncio.run(_run_node(node))
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
