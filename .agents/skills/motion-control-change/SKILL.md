---
name: motion-control-change
description: Change the mower command path, CAN protocol, STM32 firmware, or Jetson control bridge while preserving motion-safety boundaries.
---

# Motion-control change

Use this skill for changes that can affect command interpretation or motor
output. Read these before editing:

- [`docs/interfaces/can-motion.md`](../../../docs/interfaces/can-motion.md)
- [`docs/architecture/safety-and-trust-boundaries.md`](../../../docs/architecture/safety-and-trust-boundaries.md)
- [`docs/nvidia_jetson/README.md`](../../../docs/nvidia_jetson/README.md) or
  [`docs/stm32/README.md`](../../../docs/stm32/README.md), as applicable

Preserve the STM32 as the independent final safety authority. A Jetson timeout
or ROS validation must not replace MCU frame validation, watchdog behaviour, or
safe disabled output.

Update both producer and consumer, their protocol tests, and canonical STM32
documentation for a CAN contract change. Run offline/bench validation first.
Do not flash firmware or command a physical mower without explicit
authorization for the hardware target.
