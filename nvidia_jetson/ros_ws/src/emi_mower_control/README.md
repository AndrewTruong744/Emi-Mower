# Emi Mower control

This package owns the ROS-to-STM32 CAN part of the manual-command path:

```text
app Zenoh put mower/<mower_id>/joystick {"x": ..., "y": ...}
  -> zenoh_gateway -> /teleop/cmd_vel (geometry_msgs/TwistStamped)
  -> stm32_bridge -> SocketCAN frame -> STM32 Embassy
```

The app/backend-facing Zenoh route is owned by the separate
`emi_mower_zenoh_gateway` package. `stm32_bridge` only consumes the typed ROS
command, so it has no native Zenoh client or dependency on the AsyncAPI route.

## Required runtime environment

The launch files provide these values. They are listed here to make direct
execution unambiguous:

```text
MOWER_ID=mower-01
ZENOH_CONFIG=/path/to/zenoh_client.json5
STM32_CAN_INTERFACE=can0
COMMAND_TIMEOUT_MS=200
```

The ROS container connects to, but does not create, the router. Mount the mower
mTLS certificate bundle at `/etc/mower/certs`, matching
`emi_mower_bringup/config/zenoh_client.json5`. For the real launch, expose the
host's configured SocketCAN interface by using host networking.

## Safety boundary

The Jetson sends a frame every 20 ms and changes stale ROS input to a disabled,
zero-velocity CAN frame after 200 ms. This is not the final safety mechanism.
The STM32 Embassy task independently verifies the frame, rejects stale sequence
numbers, enforces its own watchdog, and makes the motors safe on any fault.
The exact protocol is documented in `../../../../../stm32/README.md`.
