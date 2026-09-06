# Backend and fleet services

The Python/FastAPI backend owns fleet and user records, mower provisioning,
Zenoh ACL reconciliation, telemetry persistence, and service integrations. It
also owns the native Zenoh contract at
[`backend/zenoh_asyncapi.yaml`](../../backend/zenoh_asyncapi.yaml).

## Backend guides

- [Development](development.md) — setup, local stack, migrations, and routine
  commands.
- [Architecture and folder structure](architecture.md) — backend layers and
  technology choices.
- [Docker](docker.md) — Dockerfiles, Compose stacks, and service boundaries.
- [Zenoh routers and ACL startup](zenoh-routers.md) — router planes,
  configuration files, and `add-all-acls` reconciliation.
- [Zenoh handlers and paths](zenoh.md) — query/reply behavior and backend
  route ownership.
- [AsyncAPI type generation](asyncapi-generation.md) — source of truth,
  generated outputs, and regeneration workflow.
- [PostgreSQL models](models.md) — tables and relationships.
- [Valkey](valkey.md) — cache, telemetry-buffer, and credential-expiry keys.
- [Certificates](certificates.md) — certificate roles and key-handling rules.
- [Mower initialization](mower-initialization.md) — physical provisioning and
  local simulated-mower lifecycle.
- [LiveKit](livekit.md) — publisher/viewer credential flows.
- [Scripts](scripts.md) — one-shot tools and persistent worker lifecycles.
- [Testing and quality](testing.md) — pytest modes, coverage, linting, and
  formatting.

Changes to a route or telemetry schema must follow the
[Zenoh contract workflow](../interfaces/zenoh.md). Changes to mower identity or
credentials must follow [mower provisioning](../operations/mower-provisioning.md).
