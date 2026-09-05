#!/usr/bin/env python3
"""Retrieve the latest verified boundary cutout and place it on the mower."""

import json
import os
from pathlib import Path

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import zenoh

from emi_mower_bringup.zenoh_paths import mower_cutout_download_url_path
from emi_mower_bringup.cutout_download import download_cutout


def zenoh_config() -> zenoh.Config:
    path = os.environ.get("ZENOH_CONFIG") or os.environ.get("ZENOH_SESSION_CONFIG_URI")
    return zenoh.Config.from_file(path) if path else zenoh.Config()


def reply_payload(reply: object) -> bytes:
    payload = reply.ok.payload  # type: ignore[attr-defined]
    return payload.to_bytes() if hasattr(payload, "to_bytes") else bytes(payload)


class BoundaryCutoutNode(Node):
    def __init__(self) -> None:
        super().__init__("boundary_cutout_node")
        self.declare_parameter("mower_id", os.environ.get("MOWER_ID", "mower-01"))
        self.declare_parameter("download_directory", "/var/lib/emi-mower/cutouts")
        self.declare_parameter("poll_seconds", 15.0)
        self.mower_id = str(self.get_parameter("mower_id").value)
        self.download_directory = Path(str(self.get_parameter("download_directory").value))
        self.key_expr = mower_cutout_download_url_path(self.mower_id)
        self.session = None
        self.downloaded_cutout_id: str | None = None
        self.publisher = self.create_publisher(String, "/mower/boundary_cutout_path", 10)
        self.create_timer(float(self.get_parameter("poll_seconds").value), self.poll)

    def _session(self):
        if self.session is None:
            self.session = zenoh.open(zenoh_config())
        return self.session

    def _request_download(self) -> dict[str, object] | None:
        for reply in self._session().get(
            self.key_expr, payload=b"{}", target=zenoh.QueryTarget.BEST_MATCHING
        ):
            if reply.ok:
                response = json.loads(reply_payload(reply).decode("utf-8"))
                if not response.get("cutout_id") or not response.get("download_url"):
                    raise RuntimeError("backend returned an invalid cutout download response")
                return response
        return None

    def poll(self) -> None:
        try:
            response = self._request_download()
            if response is None or response["cutout_id"] == self.downloaded_cutout_id:
                return
            extension = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}.get(
                str(response.get("content_type")), "png"
            )
            target = self.download_directory / f"{response['cutout_id']}.{extension}"
            download_cutout(str(response["download_url"]), target)
            self.downloaded_cutout_id = str(response["cutout_id"])
            self.publisher.publish(String(data=str(target)))
            self.get_logger().info(f"Downloaded boundary cutout to {target}")
        except Exception as error:
            self.get_logger().warning(f"Boundary cutout refresh failed: {error}")

    def destroy_node(self):
        if self.session is not None:
            self.session.close()
        return super().destroy_node()


def main() -> None:
    rclpy.init()
    node = BoundaryCutoutNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
