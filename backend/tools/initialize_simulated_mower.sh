#!/usr/bin/env bash
# Create one local-only mower simulator with its own Compose project and swtpm state.
set -euo pipefail

usage() {
  echo "Usage: $0 --serial-number SERIAL --nickname NAME [--mower-id UUID]" >&2
}

serial_number=""
nickname=""
mower_id=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --serial-number) serial_number="${2:-}"; shift 2 ;;
    --nickname) nickname="${2:-}"; shift 2 ;;
    --mower-id) mower_id="${2:-}"; shift 2 ;;
    *) usage; exit 2 ;;
  esac
done
if [[ -z "$serial_number" || -z "$nickname" ]]; then usage; exit 2; fi
if [[ -z "$mower_id" ]]; then mower_id="$(python3 -c 'import uuid; print(uuid.uuid4())')"; fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
backend_dir="$(cd "${script_dir}/.." && pwd)"
repo_dir="$(cd "${backend_dir}/.." && pwd)"
jetson_dir="${repo_dir}/nvidia_jetson"
short_id="${mower_id:0:8}"
mower_dir="${jetson_dir}/.sim/mowers/${mower_id}"
env_file="${mower_dir}/mower.env"
credential_dir="${mower_dir}/credentials"
tpm_state_dir="${mower_dir}/swtpm-state"
project="mower-${short_id}"
mkdir -p "$credential_dir" "$tpm_state_dir"
chmod 0700 "$mower_dir" "$credential_dir" "$tpm_state_dir"

cat > "$env_file" <<EOF
MOWER_ID=${mower_id}
MOWER_CREDENTIAL_DIR=${credential_dir}
ZENOH_ROUTER_ENDPOINT=tls/host.docker.internal:7448
ZENOH_VERIFY_NAME_ON_CONNECT=false
MOWER_LAUNCH=sim
SWTPM_STATE_DIR=${tpm_state_dir}
TPM_TRANSPORT=swtpm
EOF
chmod 0600 "$env_file"

compose=(docker compose --project-name "$project" --env-file "$env_file" -f "${jetson_dir}/docker-compose.yml" -f "${jetson_dir}/docker-compose.sim-tpm.yml")
# Rebuild this tiny local-only sidecar so changes to the emulator entrypoint
# are exercised rather than silently reusing an older image tag.
MOWER_ENV_FILE="$env_file" "${compose[@]}" up --build -d swtpm
MOWER_ENV_FILE="$env_file" "${compose[@]}" run --build --rm tpm-init

cd "$backend_dir"
# Share the compose credentials from backend/.env, but use the host-networked
# development stack's published PostgreSQL and Valkey ports rather than the
# workstation defaults in that file.
set -a
. "$backend_dir/.env"
set +a
POSTGRES_HOST=127.0.0.1 \
POSTGRES_PORT="${LOCAL_POSTGRES_PORT:-15432}" \
VALKEY_HOST=127.0.0.1 \
uv run python -m src.scripts.provision_mower \
  --mower-id "$mower_id" \
  --serial-number "$serial_number" \
  --nickname "$nickname" \
  --output-dir "$credential_dir" \
  --jetson-env-file "$env_file" \
  --mower-cert-dir "$credential_dir" \
  --router-endpoint tls/host.docker.internal:7448 \
  --no-verify-name-on-connect \
  --mower-launch sim \
  --device-root-public-key "$tpm_state_dir/device-root-public.pem"

printf '\nTPM_TRANSPORT=swtpm\nSWTPM_STATE_DIR=%s\n' "$tpm_state_dir" >> "$env_file"
MOWER_ENV_FILE="$env_file" "${compose[@]}" up -d ros
echo "Started simulated mower ${mower_id} as Compose project ${project}"
