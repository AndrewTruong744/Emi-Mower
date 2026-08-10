# Backend

## Install

Install [uv](https://docs.astral.sh/uv/) and install the Python dependencies:

```bash
uv sync
```

PostgreSQL, Valkey, and Zenoh are provided by Docker Compose. You do not need
to install any of them directly on the host when using the Compose workflow.

## Local Docker Compose

Copy `.env.example` to `.env` and fill in the required application settings,
including `JWT_SECRET`, database credentials, and certificate paths. Start the
complete local stack from this directory:

```bash
docker compose -f local-docker-compose.yml up -d
docker compose -f local-docker-compose.yml ps
docker compose -f local-docker-compose.yml logs -f backend
```

The stack uses host networking on Linux. It includes PostgreSQL, Valkey,
Zenoh, the backend, the telemetry worker, the expired-credential worker, and
the one-shot ACL bootstrap service. To start only the persistent services and
backend, run:

```bash
docker compose -f local-docker-compose.yml up -d \
  postgres valkey zenoh-mtls zenoh-app backend
docker compose -f local-docker-compose.yml run --rm add-all-acls
```

Start the background workers separately when needed:

```bash
docker compose -f local-docker-compose.yml up -d upload-telemetry remove-usrpwds
```

Stop the stack with `docker compose -f local-docker-compose.yml down`. The
PostgreSQL and Valkey volumes persist across restarts. `down -v` also removes
those volumes and all data stored in them.

### Access PostgreSQL

Open `psql` inside the Compose PostgreSQL container so the credentials from the
container environment are used:

```bash
docker compose -f local-docker-compose.yml exec postgres \
  sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

Useful `psql` commands include `\dt` to list tables, `SELECT ...` to inspect
rows, and `\q` to exit. Because the local stack uses host networking, a host
`psql` client can also connect to `127.0.0.1` on `${POSTGRES_PORT:-5432}`.

### Access Valkey

Open the Valkey CLI inside its container:

```bash
docker compose -f local-docker-compose.yml exec valkey valkey-cli
```

Use `SCAN 0` to list keys, `TYPE <key>` to identify a value, `GET <key>` for
strings, `HGETALL <key>` for hashes, and `QUIT` to exit. The local stack
persists Valkey data in the `valkey-data` volume.

## Disposable integration-test Compose stack

The integration suite starts `docker-compose.test.yml` as needed. It uses a
bridge network, maps PostgreSQL to host port `15432` and Valkey to host port
`16379`, and has no database or cache volumes.

To inspect those services manually:

```bash
docker compose -f docker-compose.test.yml up -d postgres valkey
docker compose -f docker-compose.test.yml exec postgres \
  psql -U test -d emi_mower_test
docker compose -f docker-compose.test.yml exec valkey valkey-cli
```

The same services are available from the host with `psql -h 127.0.0.1 -p
15432 -U test -d emi_mower_test` and `valkey-cli -h 127.0.0.1 -p 16379`.
Stop the disposable stack with:

```bash
docker compose -f docker-compose.test.yml down
```

## Certificates

The CA, FastAPI, and Zenoh certificates are in `certs/`. Reissue them when
the development hostname or IP changes. Zenoh server certificates must include
every hostname used by clients in their Subject Alternative Name (SAN) list.

### Certificate Authority

```bash
openssl genrsa -aes256 -out ca.key 4096
openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 -out ca.crt \
  -subj "/CN=Emi Mower CA/O=EmiSamaTechnologies/C=US"
```

### FastAPI server certificate

Update the IP or DNS names in `server.cnf`, then run:

```bash
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr -config server.cnf
openssl x509 -req -in server.csr \
  -CA ../ca/ca.crt -CAkey ../ca/ca.key -CAcreateserial \
  -out server.crt -days 365 -sha256 \
  -extfile server.cnf -extensions req_ext
```

### Zenoh router certificates

Update the hostnames and IPs in `router.cnf`, then run:

```bash
openssl genrsa -out router.key 2048
openssl req -new -key router.key -out router.csr -config router.cnf
openssl x509 -req -in router.csr \
  -CA ../ca/ca.crt -CAkey ../ca/ca.key -CAcreateserial \
  -out router.crt -days 365 -sha256 \
  -extfile router.cnf -extensions req_ext
```

## Migrations

```bash
uv run alembic revision --autogenerate -m "message"
uv run alembic upgrade head
```

## Generated Zenoh types

```bash
npm install --global @asyncapi/cli
./scripts/generate_types.sh
```

Run the generation command from `backend/`.

## Linting

```bash
uv run ruff check .
uv run ruff check . --fix
uv run ruff format .
```

## Tests

Run the fast, Docker-free service and Zenoh unit tests:

```bash
uv run pytest -m 'not repository and not api and not zenoh_integration'
```

Run the complete suite, including disposable PostgreSQL/Valkey Testcontainers
and the Compose API/Zenoh stack:

```bash
uv run pytest --run-integration
```
