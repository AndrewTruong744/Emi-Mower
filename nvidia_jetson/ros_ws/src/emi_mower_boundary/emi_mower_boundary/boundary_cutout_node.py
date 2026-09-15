#!/usr/bin/env python3
"""Persist verified cutouts received from the native Zenoh gateway.

This ROS-only node deliberately has no Zenoh dependency. Future cutout
interpretation belongs here after a download succeeds.
"""

import os
from pathlib import Path

import rclpy
from emi_mower_interfaces.msg import CutoutDownload
from rclpy.node import Node
from std_msgs.msg import String

from emi_mower_boundary.cutout_download import download_cutout


CUTOUT_DOWNLOAD_TOPIC = "/mower/boundary_cutout/download"
CUTOUT_PATH_TOPIC = "/mower/boundary_cutout_path"
EXTENSIONS = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}


def target_path(download_directory: Path, cutout_id: str, content_type: str) -> Path:
    """Construct a local target without allowing a remote ID to escape it."""
    if not cutout_id or cutout_id in {".", ".."} or "/" in cutout_id or "\\" in cutout_id:
        raise ValueError("cutout ID must be a non-empty filename segment")
    return download_directory / f"{cutout_id}.{EXTENSIONS.get(content_type, 'png')}"


class BoundaryCutoutNode(Node):
    def __init__(self) -> None:
        super().__init__("boundary_cutout_node")
        self.declare_parameter("download_directory", "/var/lib/emi-mower/cutouts")
        self.download_directory = Path(str(self.get_parameter("download_directory").value))
        self.downloaded_cutout_id: str | None = None
        self.publisher = self.create_publisher(String, CUTOUT_PATH_TOPIC, 10)
        self.subscription = self.create_subscription(
            CutoutDownload, CUTOUT_DOWNLOAD_TOPIC, self.handle_download, 10
        )

    def handle_download(self, response: CutoutDownload) -> None:
        if response.cutout_id == self.downloaded_cutout_id:
            return
        try:
            target = target_path(
                self.download_directory, response.cutout_id, response.content_type
            )
            download_cutout(response.download_url, target)
            self.downloaded_cutout_id = response.cutout_id
            self.publisher.publish(String(data=str(target)))
            self.get_logger().info(f"Downloaded boundary cutout to {target}")
        except Exception as error:
            self.get_logger().warning(f"Boundary cutout download failed: {error}")


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
