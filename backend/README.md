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

## Server key (in deploy_{environment})

- make sure to edit IP.3 to point to your development ipv4 addr (ip a)
- openssl genrsa -out server.key 2048
- openssl req -new -key server.key -out server.csr -config server.cnf
- openssl x509 -req -in server.csr \
  -CA ../ca/ca.crt -CAkey ../ca/ca.key -CAcreateserial \
  -out server.crt -days 365 -sha256 \
  -extfile server.cnf -extensions req_ext

## Mosquitto (MQTT Broker)

- sudo apt update
- sudo apt install mosquitto mosquitto-clients -y
- sudo mv /etc/mosquitto/mosquitto.conf /etc/mosquitto/mosquitto.conf.bak
- sudo ln -s /home/andrew/Repos/Emi-Mower/backend/mosquitto.conf /etc/mosquitto/mosquitto.conf
- sudo cp /home/andrew/Repos/Emi-Mower/backend/certs/ca.crt /etc/mosquitto/certs/
- sudo cp /home/andrew/Repos/Emi-Mower/backend/certs/server.crt /etc/mosquitto/certs/
- sudo cp /home/andrew/Repos/Emi-Mower/backend/certs/server.key /etc/mosquitto/certs/
- sudo chown -R mosquitto:mosquitto /etc/mosquitto/certs
- sudo chmod 600 /etc/mosquitto/certs/server.key
- sudo chmod 644 /etc/mosquitto/certs/server.crt /etc/mosquitto/certs/ca.crt
- sudo systemctl restart mosquitto.service
- systemctl status mosquitto.service

## Remember to get secret keys

- Certificate Authority keys
- GCP serviceAccount.json

# To Run

- uv run uvicorn src.main:app --host 0.0.0.0 --port 8000

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
