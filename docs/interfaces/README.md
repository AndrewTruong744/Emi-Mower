# Interfaces

These interfaces cross independent runtime or trust boundaries. Identify and
update the authoritative source before editing consumers.

- [Zenoh telemetry and command contract](zenoh.md)
- [Jetson-to-STM32 CAN motion contract](can-motion.md)
- ROS messages are owned by `nvidia_jetson/ros_ws/src/emi_mower_interfaces`.

When a change crosses app, backend, Jetson, or STM32 code, document the
compatibility impact and run the relevant contract tests.
