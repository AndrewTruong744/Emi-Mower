# Jetson and ROS runtime

The Jetson runs the ROS Jazzy workspace in Docker. It connects to an external
Zenoh router, hosts ROS packages for bringup, control, telemetry gateway, and
LiveKit integration, and bridges command flow to STM32 SocketCAN.

Use [`nvidia_jetson/README.md`](../../nvidia_jetson/README.md) for Docker,
device, local tooling, and test commands. The real-mower Compose override
exposes devices and CAN; simulation uses the default launch path.

Read [CAN motion](../interfaces/can-motion.md) before changing
`emi_mower_control`, and [Zenoh](../interfaces/zenoh.md) before changing the
gateway or native routes. Third-party camera and lidar drivers are Git
submodules: avoid treating them as locally owned mower code.
