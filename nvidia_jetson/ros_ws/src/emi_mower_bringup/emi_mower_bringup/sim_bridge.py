#!/usr/bin/env python3
"""Send this mower's ROS simulation controls to the local MuJoCo process."""

import json
import math
import os
import socket
import threading
import time

import rclpy
from geometry_msgs.msg import TwistStamped
from rclpy.node import Node
from std_msgs.msg import Bool


COMMAND_TIMEOUT = 0.2


class SimBridge(Node):
    def __init__(self):
        super().__init__("sim_bridge")
        self.mower_id = os.environ["MOWER_ID"]
        endpoint = os.environ.get("MUJOCO_BRIDGE_ENDPOINT", "host.docker.internal:8765")
        self.host, port = endpoint.rsplit(":", 1)
        self.port = int(port)
        self.lock = threading.Lock()
        self.linear = 0.0
        self.angular = 0.0
        self.last_command = 0.0
        self.blade = False
        self.last_blade = 0.0
        self.create_subscription(TwistStamped, "/sim/cmd_vel", self.on_velocity, 10)
        self.create_subscription(Bool, "/sim/blade_enable", self.on_blade, 10)
        self.worker = threading.Thread(target=self.send_loop, daemon=True)
        self.worker.start()

    def on_velocity(self, message):
        linear = message.twist.linear.x
        angular = message.twist.angular.z
        if not math.isfinite(linear) or not math.isfinite(angular):
            return
        with self.lock:
            self.linear = max(-1.0, min(1.0, linear))
            self.angular = max(-1.0, min(1.0, angular))
            self.last_command = time.monotonic()

    def on_blade(self, message):
        with self.lock:
            self.blade = bool(message.data)
            self.last_blade = time.monotonic()

    def command(self):
        with self.lock:
            fresh = time.monotonic() - self.last_command <= COMMAND_TIMEOUT
            return {
                "linear": self.linear if fresh else 0.0,
                "angular": self.angular if fresh else 0.0,
                "blade": self.blade and time.monotonic() - self.last_blade <= COMMAND_TIMEOUT,
            }

    def send_loop(self):
        while rclpy.ok():
            try:
                with socket.create_connection((self.host, self.port), timeout=3) as stream:
                    stream.settimeout(3)
                    stream.sendall((json.dumps({"mower_id": self.mower_id}) + "\n").encode())
                    self.get_logger().info("connected to MuJoCo")
                    while rclpy.ok():
                        stream.sendall((json.dumps(self.command()) + "\n").encode())
                        time.sleep(0.05)
            except (OSError, ValueError) as error:
                self.get_logger().warn(f"MuJoCo unavailable: {error}")
                time.sleep(2)


def main():
    rclpy.init()
    node = SimBridge()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
