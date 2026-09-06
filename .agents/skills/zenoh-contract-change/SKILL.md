---
name: zenoh-contract-change
description: Change native Zenoh mower routes or telemetry schemas shared by the app, backend, and Jetson gateway.
---

# Zenoh contract change

Read [`docs/interfaces/zenoh.md`](../../../docs/interfaces/zenoh.md),
[`docs/backend/README.md`](../../../docs/backend/README.md), and
[`docs/nvidia_jetson/README.md`](../../../docs/nvidia_jetson/README.md).

Edit `backend/zenoh_asyncapi.yaml` before consumers. Regenerate bindings from
`backend/` with `sh tools/generate_types.sh`; do not hand-edit generated Python,
TypeScript, or Rust files.

Check route scoping by `mower_id`, backward compatibility, and the impact on
app subscriptions and Jetson translation. Run backend contract tests and all
affected app and Jetson checks before completion.
