#!/usr/bin/env bash
set -euo pipefail

: "${ZENOH_ROUTER_ENDPOINT:=tls/host.docker.internal:7448}"
: "${ZENOH_VERIFY_NAME_ON_CONNECT:=true}"
: "${ZENOH_BOOTSTRAP_ENDPOINT:=tls/host.docker.internal:7449}"
: "${ZENOH_BOOTSTRAP_VERIFY_NAME_ON_CONNECT:=true}"
: "${MOWER_ID:?MOWER_ID must be set by the provisioned Jetson .env file}"

export MOWER_ID ZENOH_ROUTER_ENDPOINT ZENOH_VERIFY_NAME_ON_CONNECT
export ZENOH_BOOTSTRAP_ENDPOINT ZENOH_BOOTSTRAP_VERIFY_NAME_ON_CONNECT
mkdir -p /run/emi-mower
envsubst < /opt/emi-mower/zenoh_client.json5.in > /run/emi-mower/zenoh_client.json5
envsubst < /opt/emi-mower/zenoh_bootstrap_client.json5.in > /run/emi-mower/zenoh_bootstrap_client.json5
export ZENOH_SESSION_CONFIG_URI=/run/emi-mower/zenoh_client.json5
export ZENOH_CONFIG=/run/emi-mower/zenoh_client.json5
export ZENOH_BOOTSTRAP_CONFIG=/run/emi-mower/zenoh_bootstrap_client.json5
export RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:=rmw_zenoh_cpp}"

if [[ ! -r /etc/mower/certs/mower.crt || ! -r /etc/mower/certs/mower.key || ! -r /etc/mower/certs/root_ca.pem ]]; then
  echo "warning: Zenoh mTLS credentials are not all mounted at /etc/mower/certs; clients will retry until they are available" >&2
fi

set +u
source /opt/ros/jazzy/setup.bash
source /ws/install/setup.bash
set -u
exec "$@"
