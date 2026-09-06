---
name: fleet-release
description: Prepare or assess a deployment of Jetson, backend, app, or firmware changes to physical mower fleet targets.
---

# Fleet release

Read [`docs/operations/fleet-rollout-and-rollback.md`](../../../docs/operations/fleet-rollout-and-rollback.md),
[`docs/operations/incident-response.md`](../../../docs/operations/incident-response.md),
and the documentation for each changed subsystem.

Prepare a target list, deployable version, configuration/certificate impact,
verification evidence, and rollback artifact. Run appropriate offline and
simulation or bench checks first. Use an explicitly selected canary before a
larger rollout.

Do not deploy, flash firmware, or command a physical mower without explicit
authorization for the environment and target mower(s). Stop expansion on an
unexpected canary result and preserve diagnostic evidence before retrying.
