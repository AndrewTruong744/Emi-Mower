"""Offline tests for the LiveKit video sender.

The ROS, Zenoh, and LiveKit modules are replaced with tiny test doubles when
this file is run outside a sourced ROS installation.  The publish test never
creates a real Zenoh session, socket, or LiveKit connection.
"""

from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest


PACKAGE_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))


def _install_import_stubs() -> None:
    if "rclpy" not in sys.modules:
        rclpy = types.ModuleType("rclpy")

        class Node:
            def __init__(self, name: str) -> None:
                self.name = name

            def declare_parameter(self, *_args: object) -> None:
                return None

            def get_parameter(self, name: str) -> SimpleNamespace:
                return SimpleNamespace(value={"camera_topic": "/camera", "mower_id": "mower-01", "video_fps": 15, "video_bitrate": 2_000_000}[name])

            def create_subscription(self, *_args: object) -> object:
                return object()

            def get_logger(self) -> SimpleNamespace:
                return SimpleNamespace(info=lambda *_a: None, error=lambda *_a: None, warning=lambda *_a: None)

            def destroy_node(self) -> bool:
                return True

        rclpy.ok = lambda: True
        rclpy.spin = lambda *_args: None
        rclpy.init = lambda *_args, **_kwargs: None
        rclpy.shutdown = lambda: None
        rclpy.node = types.ModuleType("rclpy.node")
        rclpy.node.Node = Node
        sys.modules["rclpy"] = rclpy
        sys.modules["rclpy.node"] = rclpy.node

    if "sensor_msgs.msg" not in sys.modules:
        sensor_msgs = types.ModuleType("sensor_msgs")
        sensor_msgs.msg = types.ModuleType("sensor_msgs.msg")
        sensor_msgs.msg.Image = type("Image", (), {})
        sys.modules["sensor_msgs"] = sensor_msgs
        sys.modules["sensor_msgs.msg"] = sensor_msgs.msg

    if "zenoh" not in sys.modules:
        zenoh = types.ModuleType("zenoh")

        class Config:
            @classmethod
            def from_file(cls, path: str) -> tuple[str, str]:
                return ("from_file", path)

        zenoh.Config = Config
        zenoh.QueryTarget = SimpleNamespace(BEST_MATCHING="BEST_MATCHING")
        zenoh.open = lambda *_args, **_kwargs: pytest.fail("offline test opened Zenoh")
        sys.modules["zenoh"] = zenoh

    if "livekit.rtc" not in sys.modules:
        livekit = types.ModuleType("livekit")
        rtc = types.ModuleType("livekit.rtc")
        rtc.Room = type("Room", (), {})
        rtc.VideoSource = type("VideoSource", (), {})
        rtc.LocalVideoTrack = type("LocalVideoTrack", (), {})
        rtc.TrackPublishOptions = type("TrackPublishOptions", (), {})
        rtc.VideoEncoding = type("VideoEncoding", (), {})
        rtc.VideoFrame = type("VideoFrame", (), {})
        rtc.VideoBufferType = SimpleNamespace(RGB24="RGB24")
        rtc.TrackSource = SimpleNamespace(SOURCE_CAMERA="SOURCE_CAMERA")
        livekit.rtc = rtc
        sys.modules["livekit"] = livekit
        sys.modules["livekit.rtc"] = rtc


_install_import_stubs()

from emi_mower_py.nodes import livekit_node  # noqa: E402


def stamp(sec: int = 1, nanosec: int = 500_000_000) -> SimpleNamespace:
    return SimpleNamespace(sec=sec, nanosec=nanosec)


def test_ros_image_is_converted_to_packed_rgb24() -> None:
    msg = SimpleNamespace(
        width=2,
        height=1,
        encoding="bgr8",
        step=8,
        data=bytes([1, 2, 3, 4, 5, 6, 99, 100]),
        header=SimpleNamespace(stamp=stamp()),
    )

    frame = livekit_node.LiveKitNode._ros_image_to_rgb24(msg)

    assert (frame.width, frame.height) == (2, 1)
    assert frame.data == bytes([3, 2, 1, 6, 5, 4])
    assert frame.timestamp_us == 1_500_000


def test_zenoh_config_uses_the_ros_session_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("ZENOH_CONFIG", raising=False)
    config_path = tmp_path / "zenoh-client.json5"
    config_path.write_text('{mode: "client"}')
    monkeypatch.setenv("ZENOH_SESSION_CONFIG_URI", str(config_path))

    config = livekit_node._zenoh_config()
    if isinstance(config, tuple):
        assert config == ("from_file", str(config_path))
    else:
        assert config.get_json("mode") == '"client"'


def test_upload_query_uses_zenoh_19_best_matching_value() -> None:
    class Reply:
        ok = SimpleNamespace(
            payload=b'{"token":"token","url":"wss://livekit.example"}'
        )
        err = None

    class Session:
        def __init__(self) -> None:
            self.calls: list[tuple[str, bytes, object]] = []

        def get(self, key: str, *, payload: bytes, target: object) -> list[Reply]:
            self.calls.append((key, payload, target))
            return [Reply()]

    node = livekit_node.LiveKitNode.__new__(livekit_node.LiveKitNode)
    node.zenoh_session = Session()
    node.upload_key = "mower/mower-01/livekit/upload"

    response = node._request_upload_token()

    assert response["token"] == "token"
    assert node.zenoh_session.calls == [
        (
            "mower/mower-01/livekit/upload",
            b"{}",
            livekit_node.zenoh.QueryTarget.BEST_MATCHING,
        )
    ]


def test_publish_camera_publishes_rgb_track_and_frames(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asyncio.run(_test_publish_camera_publishes_rgb_track_and_frames(monkeypatch))


async def _test_publish_camera_publishes_rgb_track_and_frames(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    published: dict[str, object] = {}

    class FakeVideoFrame:
        def __init__(self, width: int, height: int, kind: object, data: bytes) -> None:
            self.width = width
            self.height = height
            self.kind = kind
            self.data = data

    class FakeSource:
        def __init__(self, width: int, height: int) -> None:
            self.width = width
            self.height = height
            self.frames: list[tuple[FakeVideoFrame, int]] = []
            published["source"] = self

        def capture_frame(self, frame: FakeVideoFrame, *, timestamp_us: int) -> None:
            self.frames.append((frame, timestamp_us))

        async def aclose(self) -> None:
            published["source_closed"] = True

    class FakeTrack:
        pass

    class FakeTrackFactory:
        @staticmethod
        def create_video_track(name: str, source: FakeSource) -> FakeTrack:
            published["track_name"] = name
            published["track_source"] = source
            return FakeTrack()

    class FakeEncoding:
        def __init__(self, *, max_framerate: int, max_bitrate: int) -> None:
            self.max_framerate = max_framerate
            self.max_bitrate = max_bitrate

    class FakePublishOptions:
        def __init__(self, *, source: object, video_encoding: FakeEncoding) -> None:
            self.source = source
            self.video_encoding = video_encoding

    class Participant:
        async def publish_track(self, track: FakeTrack, options: FakePublishOptions) -> SimpleNamespace:
            published["track"] = track
            published["options"] = options
            return SimpleNamespace(sid="publication-1")

    class FakeRoom:
        def __init__(self, *, loop: asyncio.AbstractEventLoop) -> None:
            self.loop = loop
            self.name = "mower-room"
            self.local_participant = Participant()
            self.connected = False
            self.connection_checks = 0
            self.handlers: dict[str, object] = {}

        def on(self, event: str):
            def decorator(callback: object) -> object:
                self.handlers[event] = callback
                return callback

            return decorator

        async def connect(self, url: str, token: str) -> None:
            published["connect"] = (url, token)
            self.connected = True

        def isconnected(self) -> bool:
            self.connection_checks += 1
            return self.connection_checks == 1

        async def disconnect(self) -> None:
            self.connected = False
            published["disconnected"] = True

    monkeypatch.setattr(livekit_node.rtc, "Room", FakeRoom)
    monkeypatch.setattr(livekit_node.rtc, "VideoSource", FakeSource)
    monkeypatch.setattr(livekit_node.rtc, "VideoFrame", FakeVideoFrame)
    monkeypatch.setattr(livekit_node.rtc, "VideoBufferType", SimpleNamespace(RGB24="RGB24"))
    monkeypatch.setattr(livekit_node.rtc, "LocalVideoTrack", FakeTrackFactory)
    monkeypatch.setattr(livekit_node.rtc, "VideoEncoding", FakeEncoding)
    monkeypatch.setattr(livekit_node.rtc, "TrackPublishOptions", FakePublishOptions)
    monkeypatch.setattr(livekit_node.rtc, "TrackSource", SimpleNamespace(SOURCE_CAMERA="camera"))
    monkeypatch.setattr(livekit_node.rclpy, "ok", lambda: True)

    first = livekit_node.CameraFrame(2, 1, b"first", 10)
    second = livekit_node.CameraFrame(2, 1, b"second", 20)
    node = livekit_node.LiveKitNode.__new__(livekit_node.LiveKitNode)
    node.video_fps = 15
    node.video_bitrate = 2_000_000
    node._frame_queue = asyncio.Queue(maxsize=1)
    node._livekit_room = None
    node._video_source = None
    node.get_logger = lambda: SimpleNamespace(info=lambda *_a: None, warning=lambda *_a: None)

    # Seed the second frame after the first-frame wait has completed.
    calls = 0

    async def next_frame(disconnected: asyncio.Event) -> livekit_node.CameraFrame:
        nonlocal calls
        calls += 1
        if calls == 1:
            return first
        return second

    node._next_frame = next_frame
    await node._publish_camera({"url": "wss://livekit.example", "token": "token"})

    assert published["connect"] == ("wss://livekit.example", "token")
    assert published["track_name"] == "oak_rgb"
    options = published["options"]
    assert options.source == "camera"
    assert options.video_encoding.max_framerate == 15
    assert options.video_encoding.max_bitrate == 2_000_000
    source = published["source"]
    assert [(frame.data, timestamp) for frame, timestamp in source.frames] == [
        (b"first", 10),
        (b"second", 20),
    ]
    assert published["source_closed"] is True
