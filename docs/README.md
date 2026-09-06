# Emi-Mower documentation

This directory is the repository's documentation map. It explains the system,
its operational boundaries, and how each top-level subsystem fits into the
fleet. Keep executable contracts and generated artifacts in their owning source
locations; link to them here rather than copying them.

## Start here

- [System overview](architecture/system-overview.md) describes the control,
  telemetry, identity, and deployment boundaries.
- [Interfaces](interfaces/README.md) identifies the authoritative Zenoh and CAN
  contracts.
- [Operations](operations/README.md) covers provisioning, rollout, rollback,
  and incident handling.
- [Development](development/README.md) maps local workflows and verification.

## Subsystems

| Area                       | Documentation                                                                                                                    |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| Mobile app                 | [app](app/README.md) and [development](app/development.md)                                                                       |
| Backend and fleet services | [backend](backend/README.md)                                                                                                     |
| Jetson / ROS runtime       | [nvidia_jetson](nvidia_jetson/README.md)                                                                                         |
| STM32 motor controller     | [stm32](stm32/README.md)                                                                                                         |
| Cloud infrastructure       | [infrastructure](infrastructure/README.md)                                                                                       |
| Simulation                 | [simulation](simulation/README.md), [isaac-sim](isaac-sim/README.md), [ansys](ansys/README.md), and [ltspice](ltspice/README.md) |

## Documentation rules

- Update the relevant page when a public behaviour, operator procedure, or
  system boundary changes.
- Mark a document's source of truth when it describes a wire contract,
  generated code, or security material.
- Do not put certificates, private keys, tokens, customer data, or production
  endpoints in this directory.
