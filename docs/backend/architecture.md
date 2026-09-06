# Backend architecture, folder structure, and tech stack

The backend is an asynchronous Python service that owns user/fleet data,
provisioning, Zenoh ACL configuration, telemetry persistence, GCS cutout
authorization, and LiveKit credential issuance. FastAPI exposes only health
today; the app and mower use native Zenoh as the operational interface.

## Tech stack

- Python 3.12, managed with `uv`
- FastAPI and Uvicorn for process lifecycle and health endpoint
- SQLAlchemy 2 async ORM, asyncpg, Alembic, and PostgreSQL
- Valkey async client for cache-aside data, telemetry buffering, and credential
  expiry metadata
- Eclipse Zenoh Python client plus router REST admin API
- Firebase Admin for ID-token verification
- PyJWT for short-lived app-router passwords
- Google Cloud Storage signed URLs for cutouts
- LiveKit API for room-scoped publisher/viewer credentials
- Pytest, pytest-asyncio, pytest-cov, Testcontainers, Docker Compose, and Ruff

## Folder structure

```text
backend/
├── src/
│   ├── api/           FastAPI routes (currently health)
│   ├── config/        Settings, database, Valkey, HTTP, Zenoh, and router-admin clients
│   ├── models/        SQLAlchemy table mappings
│   ├── repositories/  Database and cache-aside persistence operations
│   ├── services/      Authorization and business workflows
│   ├── zenoh/         Query/message bridge, listeners, and generated bindings
│   ├── scripts/       One-shot operations and persistent workers
│   └── migrations/    Alembic migration environment and revisions
├── tests/             Unit, service, repository, route, Zenoh, and script tests
├── tools/             Contract generators and provisioning/simulation tools
├── certs/             Local trust material and certificate request configs
├── Dockerfile.*       Router-plugin and test backend images
├── *docker-compose*.yml  Local, GCS-overlay, and disposable test stacks
└── zenoh-router-*.json5  Router-plane configuration
```

## Layering rules

`listeners` translate generated Zenoh payloads to services. `services` enforce
identity, ownership, and workflow rules. `repositories` own SQLAlchemy and
Valkey reads/writes. `models` define tables; `schemas` define external/cache
payload models. `config` creates long-lived clients and settings, while `main`
owns startup/shutdown and registers Zenoh declarations.

Keep native Zenoh route strings and payload types in generated bindings. Do not
move SQL/Valkey calls into listeners or components that only coordinate
transport. Mower command handling stays in the gateway/STM32 path, not the
backend, preserving the STM32 as final motion-safety authority.

## Runtime sequence

At startup FastAPI initializes shared HTTP/Firebase resources, confirms storage
availability, opens the normal mTLS Zenoh session, declares standard handlers,
opens the TLS-only bootstrap session, and declares only renewal handlers.
Shutdown undeclares those resources and closes Zenoh, Valkey, and HTTP clients.
The telemetry and credential-cleanup loops run as separate services so their
work does not block request/reply handling.
