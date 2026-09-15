#!/bin/bash
set -euo pipefail

export STEPPATH="${STEPPATH:-/home/step}"
readonly config_path="${STEPPATH}/config/ca.json"
readonly password_file="${STEPPATH}/secrets/password"

ensure-step-ca
step-ca --password-file "${password_file}" "${config_path}" &
ca_pid=$!

cleanup() {
  kill "${ca_pid}" 2>/dev/null || true
  wait "${ca_pid}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

for _ in $(seq 1 30); do
  if step ca health --ca-url "${STEP_CA_URL:-https://localhost:9000}" >/dev/null 2>&1; then
    refresh-service-certificates
    wait "${ca_pid}"
    exit $?
  fi
  sleep 1
done

echo "step-ca did not become healthy" >&2
exit 1
