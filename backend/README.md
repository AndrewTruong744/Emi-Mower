# To install
- install uv
- install fastapi
- uv sync

## postgres
- sudo apt install -y postgresql-common ca-certificates curl
- sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh
- sudo apt update
- sudo apt install -y postgresql-18 postgresql-contrib-18
- sudo -u postgres psql

## valkey
- curl -O https://download.valkey.io/releases/valkey-9.0.0-jammy-x86_64.tar.gz
- tar -xvzf valkey-9.0.0-jammy-x86_64.tar.gz
- cd valkey-9.0.0-jammy-x86_64/
- sudo cp bin/valkey-server bin/valkey-cli /usr/local/bin/
- valkey-server &

## Tailscale
- curl -fsSL https://tailscale.com/install.sh | sh
- sudo tailscale up

## Mosquitto (MQTT Broker)
- sudo apt update
- sudo apt install mosquitto mosquitto-clients -y

# To Run
- uv run uvicorn main:app --reload

# Migrations
- uv run alembic revision --autogenerate -m "message"
- uv run alembic upgrade head

# Postgres
- sudo -u postgres psql -d EmiMower (access)

# Valkey
- valkey-server (starts server)
- valkey-cli (enters server)

# Linting
- To check: uv run ruff check .
- To lint: uv run ruff check . --fix
- To format: uv run ruff format .
