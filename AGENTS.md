# Emi-Mower agent guidance

Read [docs/README.md](docs/README.md) before changing a subsystem. Read that
subsystem's documentation page and the relevant interface page before a
cross-layer change.

For a task matching a procedure in `.agents/skills/`, read its `SKILL.md`
before acting. These repository skills are source-controlled references; install
or configure them separately when an agent runtime requires explicit skill
discovery.

## Critical invariants

- `backend/zenoh_asyncapi.yaml` is the native Zenoh contract source of truth.
  Regenerate derived Python, TypeScript, and Rust bindings; never hand-edit
  generated outputs.
- The STM32 remains the final motor safety authority. Preserve independent CAN
  validation and watchdog behaviour when changing the control path.
- The CA private key must never enter a Jetson, container image, `.env` file,
  or repository. Treat provisioning and ACL changes as fleet operations.
- Do not flash firmware, start physical motion, deploy to a fleet, rotate
  production credentials, or delete persistent fleet data without explicit
  authorization for the target and environment.

## Verification

Follow [docs/development/verification.md](docs/development/verification.md).
Run the smallest meaningful checks locally, and include every affected layer
for interface, motion-control, identity, or deployment changes.
