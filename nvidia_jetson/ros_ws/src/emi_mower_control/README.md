# Emi Mower control

This package is the manual-command path:

```text
app Zenoh put mower/<mower_id>/joystick {"x": ..., "y": ...}
  -> teleop_gateway -> /teleop/cmd_vel (geometry_msgs/TwistStamped)
  -> stm32_bridge -> Embassy UART frame -> STM32
```

`teleop_gateway` uses a native Zenoh subscription because the app's JSON
contract is not a ROS message. It publishes a standard ROS velocity message;
`rmw_zenoh_cpp` then transports ROS-to-ROS traffic through the same router.

## Required runtime environment

The launch files provide these values. They are listed here to make direct
execution unambiguous:

```text
MOWER_ID=mower-01
ZENOH_CONFIG=/path/to/zenoh_client.json5
STM32_UART_DEVICE=/dev/ttyTHS1
STM32_UART_BAUD=115200
COMMAND_TIMEOUT_MS=200
```

The ROS container and router container must share a Docker network whose
router service is named `zenoh-router`. Mount the mower mTLS certificate bundle
at `/etc/mower/certs`, matching `emi_mower_bringup/config/zenoh_client.json5`.
For the real launch, pass the Jetson UART device through to the ROS container.

## Safety boundary

The Jetson sends a frame every 20 ms and changes stale ROS input to a disabled,
zero-velocity frame after 200 ms. This is not the final safety mechanism. The
STM32 Embassy task must independently verify the frame, reject stale sequence
numbers, enforce its own watchdog, and make the motors safe on any fault.
See `docs/stm32_embassy_uart.md` for the exact protocol.
