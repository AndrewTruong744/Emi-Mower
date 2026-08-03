# To install

- install uv
- uv sync

## postgres

- sudo apt install -y postgresql-common ca-certificates curl
- sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh
- sudo apt update
- sudo apt install -y postgresql-18 postgresql-contrib-18
- sudo -u postgres psql
- CREATE DATABASE "EmiMower";
- CREATE DATABASE "EmiMower-test";
- ALTER USER postgres WITH PASSWORD 'password';

## valkey

- curl -O https://download.valkey.io/releases/valkey-9.0.0-jammy-x86_64.tar.gz
- tar -xvzf valkey-9.0.0-jammy-x86_64.tar.gz
- cd valkey-9.0.0-jammy-x86_64/
- sudo cp bin/valkey-server bin/valkey-cli /usr/local/bin/
- valkey-server &

## Certs (IMPORTANT)

- Will have to reissue for CA, server, and mower (OTA firmware update or http request)

## Certificate Authority (in ca/ folder)

- openssl genrsa -aes256 -out ca.key 4096
- openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 -out ca.crt \
  -subj "/CN=Emi Mower CA/O=EmiSamaTechnologies/C=US"

## Server key (fastapi)

- make sure to edit IP.3 to point to your development ipv4 addr (ip a)
- openssl genrsa -out server.key 2048
- openssl req -new -key server.key -out server.csr -config server.cnf
- openssl x509 -req -in server.csr \
  -CA ../ca/ca.crt -CAkey ../ca/ca.key -CAcreateserial \
  -out server.crt -days 365 -sha256 \
  -extfile server.cnf -extensions req_ext

## Server key (zenoh_app and zenoh_mtls)

- make sure to edit IP.3 to point to your development ipv4 addr (ip a)
- openssl genrsa -out router.key 2048
- openssl req -new -key router.key -out router.csr -config router.cnf
- openssl x509 -req -in router.csr \
  -CA ../ca/ca.crt -CAkey ../ca/ca.key -CAcreateserial \
  -out router.crt -days 365 -sha256 \
  -extfile router.cnf -extensions req_ext

## Zenoh
- sudo mkdir -p /etc/apt/keyrings
- curl -L https://download.eclipse.org/zenoh/debian-repo/zenoh-public-key | sudo gpg --dearmor --yes -o /etc/apt/keyrings/zenoh-public-key.gpg
- echo "deb [signed-by=/etc/apt/keyrings/zenoh-public-key.gpg] https://download.eclipse.org/zenoh/debian-repo/ /" | sudo tee /etc/apt/sources.list.d/zenoh.list > /dev/null
- sudo apt update
- sudo apt install zenoh
- sudo ufw allow 7447/tcp
- sudo ufw deny 8001/tcp

## Remember to get secret keys

- Certificate Authority keys
- GCP serviceAccount.json

## Docker / Docker Compose
- sudo apt update
- sudo apt install -y ca-certificates curl gnupg
- sudo install -m 0755 -d /etc/apt/keyrings
- curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
- sudo chmod a+r /etc/apt/keyrings/docker.gpg
- echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
- sudo apt update
- sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
- sudo usermod -aG docker $USER

# To Run

- uv run uvicorn src.main:app --host 0.0.0.0 --port 8000

# Migrations

- uv run alembic revision --autogenerate -m "message"
- uv run alembic upgrade head

# Postgres

- sudo -u postgres psql -d EmiMower (access)
- psql -U postgres -h 127.0.0.1 -d EmiMower (access)

# Valkey

- valkey-server (starts server)
- valkey-cli (enters server)

# Zenoh
- zenohd --config zenoh-router.json5 (in backend/)

# Generated Zenoh types

- npm install --global @asyncapi/cli
- ./scripts/generate_types.sh (run from backend/)

# Linting

- To check: uv run ruff check .
- To lint: uv run ruff check . --fix
- To format: uv run ruff format .

## Tests

Run the fast, Docker-free service and Zenoh unit tests:

```bash
uv run pytest -m 'not repository and not api and not zenoh_integration'
```

Run the complete suite, including disposable Postgres/Valkey Testcontainers
for cache-aside repository tests and the separate Compose API/Zenoh stack:

```bash
uv run pytest --run-integration
```

`docker-compose.test.yml` uses a distinct project, bridge network, and no
database or cache volumes. It never uses the local development Compose data.
