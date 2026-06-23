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

# To Run
- uv run uvicorn main:app --reload