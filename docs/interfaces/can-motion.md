# CAN motion contract

**Authoritative source:** [`stm32/README.md`](../../stm32/README.md), with the
implementation constants and validation in `stm32/src/can.rs`.

The Jetson sends classic CAN commands on `can0` using standard ID `0x321` at
500 kbit/s. The frame contains a protocol version, enabled flag, monotonic
sequence number, linear and angular velocity, and CRC-8/ATM.

The control path is:

```text
Zenoh joystick -> ROS /teleop/cmd_vel -> Jetson SocketCAN bridge -> STM32
```

The Jetson publishes a command every 20 ms and disables stale ROS input after
200 ms. The STM32 separately rejects malformed or replayed frames and applies
its own 200 ms watchdog. Any change to frame layout, timeout, enabled-state
semantics, or speed units must update both implementations, their tests, and
the canonical STM32 documentation.
