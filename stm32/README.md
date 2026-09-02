# STM32 Embassy motor controller

This is a standalone Rust/Embassy project for the STM32F446RE. It receives the
Jetson's ROS 2 teleoperation command over classic CAN, validates it, enforces a
separate 200 ms STM32 watchdog, then mixes it into left/right skid-steer motor
commands. It never runs ROS 2 or Zenoh on the MCU.

```text
app joystick {x, y}
  -> Zenoh gateway: y = linear, x = angular
  -> ROS /teleop/cmd_vel
  -> Jetson SocketCAN bridge (can0, ID 0x321)
  -> STM32 CAN1 -> watchdog -> skid-steer mixer -> two H-bridges
```

## CAN contract

The Jetson sends one 8-byte classic CAN data frame at 50 Hz on standard ID
`0x321` at 500 kbit/s.

| Byte | Meaning |
| --- | --- |
| 0 | Protocol version (`1`) |
| 1 | Flags; bit 0 is `enabled`, every other bit is zero |
| 2 | Monotonically increasing sequence number (`u8`) |
| 3..4 | Linear speed, `i16` little-endian mm/s |
| 5..6 | Angular speed, `i16` little-endian mrad/s |
| 7 | CRC-8/ATM of bytes 0..6 |

The MCU rejects a wrong ID in hardware, malformed/checksum-invalid data, and
replayed or ambiguous sequence numbers. A disabled frame, startup, or a command
older than 200 ms produces zero PWM and both H-bridge direction pins low.

## Pins and hardware

The F446's CAN controller needs an external 3.3 V CAN transceiver; never wire
CANH/CANL directly to the Nucleo pins. Terminate the physical bus with 120 ohms
at each end.

| Function | NUCLEO-F446RE pin |
| --- | --- |
| CAN1 RX / TX (AF9) | PB8 / PB9 |
| Left PWM / direction | PA6 (TIM3_CH1), PB0 / PB1 |
| Right PWM / direction | PB6 (TIM4_CH1), PB4 / PB5 |

`SkidSteerConfig::default()` has deliberately conservative placeholder geometry
and speed values. Measure the actual track width and safe wheel speed before
enabling traction motors. Verify H-bridge polarity with the wheels off the
ground; change the output wiring or the adapter if a motor is reversed.

## Development

On macOS, install the Rust target once:

```sh
rustup target add thumbv7em-none-eabi
cargo test
cargo fmt --check
cargo build --release --features firmware --target thumbv7em-none-eabi --bin emi-mower-stm32f446re
```

`cargo test` runs the exact protocol, sequence/watchdog, and skid-steer logic
on the host without an ARM toolchain. The `firmware` feature is required for the
Embassy binary so host linting remains fast and hardware-independent.

For hardware flashing, install `probe-rs`, connect ST-LINK, and run the same
build command with `cargo run` in place of `cargo build`.

## Renode

Build the ELF, install a current Renode release, then run:

```sh
renode --console renode/stm32f446re_can.resc
```

The script uses Renode's STM32F4 bxCAN model and creates `mowerCan`. On Linux,
create `vcan0` and instead run `renode/stm32f446re_socketcan.resc`; that script
bridges the same CAN frames used by the Jetson into Renode. Renode's SocketCAN
bridge is Linux-only, so macOS can run the base script and host tests but needs
a Linux VM/host for live SocketCAN injection. Renode does not emulate an
H-bridge, so its PWM/direction outputs should be observed as GPIO/timer state
while motor safety behavior is covered by the host tests.
