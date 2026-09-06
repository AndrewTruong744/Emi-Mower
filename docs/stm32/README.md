# STM32 motor controller

The STM32F446RE Embassy project is the final software safety boundary for motor
output. It receives the Jetson's classic CAN command, validates it, independently
enforces a watchdog, and mixes commands for two skid-steer motor outputs.

The canonical protocol, pin details, build commands, and Renode workflow are in
[`stm32/README.md`](../../stm32/README.md). Preserve its independent watchdog
and fail-safe disabled output when changing either firmware or its Jetson
producer.

Use [CAN motion](../interfaces/can-motion.md) and
[safety and trust boundaries](../architecture/safety-and-trust-boundaries.md)
for cross-layer context.
