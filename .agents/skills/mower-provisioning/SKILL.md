---
name: mower-provisioning
description: Provision, repair, or audit one mower's identity, mTLS credentials, Zenoh ACLs, and Jetson environment configuration.
---

# Mower provisioning

Read [`docs/operations/mower-provisioning.md`](../../../docs/operations/mower-provisioning.md),
[`docs/operations/fleet-rollout-and-rollback.md`](../../../docs/operations/fleet-rollout-and-rollback.md),
and [`docs/backend/README.md`](../../../docs/backend/README.md).

Use the trusted backend or factory host. Never copy the CA private key to a
Jetson, container image, `.env` file, or repository. Keep issued private keys
out of command output and version control.

Before issuing, replacing, revoking, or reconciling production credentials,
obtain explicit target and environment authorization. Verify the resulting
mower identity can access only its intended routes, then record the outcome
through the team's approved operational channel.
