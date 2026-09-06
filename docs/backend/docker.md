# Docker and Compose

The backend has two Dockerfiles and three Compose definitions. Use the local
stack for development and the disposable test stack for integration tests; do
not treat either as a fleet deployment recipe.

## Dockerfiles

| File                                                         | Image purpose                                                                                                                                                                                             |
| ------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`Dockerfile.zenoh-app`](../../backend/Dockerfile.zenoh-app) | Starts from the official Zenoh 1.9 image and installs the matching remote-API plugin for `amd64` or `arm64`. The download is checksum-verified because the plugin enables the app's WebSocket connection. |
| [`Dockerfile.test`](../../backend/Dockerfile.test)           | A Python 3.12 backend image with `uv`, locked runtime dependencies, and the source tree. The disposable Compose test stack uses it for FastAPI.                                                           |

The local backend and worker services use `python:3.12-slim`, mount the working
tree, install `uv`, and run `uv sync --frozen` at container start. That favors
fast iteration; it is not an immutable production image.

## Compose files

| File                                                                         | Scope                       | Contents and lifetime                                                                                                                                                                    |
| ---------------------------------------------------------------------------- | --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`local-docker-compose.yml`](../../backend/local-docker-compose.yml)         | Local development           | Host-networked PostgreSQL, Valkey, three Zenoh routers, FastAPI, a telemetry worker, a credential-expiry worker, and the one-shot ACL reconciler. PostgreSQL and Valkey volumes persist. |
| [`docker-compose.test.yml`](../../backend/docker-compose.test.yml)           | Automated integration tests | Bridge-networked PostgreSQL, Valkey, test Zenoh routers, and FastAPI. It has no persistent data volumes and maps test-only host ports. Pytest starts and removes it.                     |
| [`local-docker-compose.gcs.yml`](../../backend/local-docker-compose.gcs.yml) | Optional local overlay      | Mounts a developer-provided Google Application Default Credentials file into the backend. It requires an explicit host path and must never be committed.                                 |

## Local stack lifecycle

Copy `backend/.env.example` to an ignored `backend/.env`, set required database
and service values, then start the complete stack from `backend/`:

```sh
docker compose -f local-docker-compose.yml up -d
docker compose -f local-docker-compose.yml ps
docker compose -f local-docker-compose.yml logs -f backend
```

For a minimal persistent stack, start PostgreSQL, Valkey, the app and mTLS
routers, and FastAPI, then run `add-all-acls` separately. Start the two worker
services when testing telemetry persistence or credential expiry.

`docker compose ... down` stops the stack while retaining the local PostgreSQL
and Valkey volumes. `down -v` irreversibly removes that local data; use it only
when that loss is intended. The test Compose teardown removes its own volumes
automatically because the stack is disposable.

## Health and dependencies

PostgreSQL and Valkey expose health checks. FastAPI waits for those services and
the three routers, applies Alembic migrations, then serves `/health`. The
telemetry worker, expired-password worker, and ACL reconciler wait for the
backend health check. This ordering avoids starting a worker before its storage
and router dependencies exist, but an already-running system still needs normal
operational monitoring and retries.
