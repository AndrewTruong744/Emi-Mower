# STM32 Embassy UART contract

`stm32_bridge` sends one 14-byte frame at 50 Hz. The STM32 must decode this
frame in its Embassy UART receive task, reject a bad magic/version/CRC or a
non-increasing sequence, and make the motors safe when no valid frame arrives
within its watchdog interval. The STM32 is the final authority for e-stop,
motor-driver faults, current limits, and its command timeout.

```text
bytes 0..1   ASCII "EM"
byte  2      protocol version (1)
byte  3      enabled (0 or 1)
bytes 4..7   sequence number, unsigned little-endian u32
bytes 8..9   target linear velocity in mm/s, signed little-endian i16
bytes 10..11 target angular velocity in mrad/s, signed little-endian i16
bytes 12..13 CRC-16/XMODEM of bytes 0..11, little-endian u16
```

The packet layout and CRC implementation in `src/lib.rs` are deliberately
allocation-free so the same algorithm can be copied into the existing Embassy
firmware project without adding ROS or Zenoh to the STM32.
