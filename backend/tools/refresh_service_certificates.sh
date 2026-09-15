#!/bin/bash
# Refresh non-CA identities into their own Docker volumes.
set -euo pipefail

: "${STEPPATH:=/home/step}"
: "${STEP_CA_URL:=https://localhost:9000}"
: "${SERVICE_CERT_RENEW_WITHIN:=720h}"
: "${ZENOH_ROUTER_SANS:=localhost,127.0.0.1,host.docker.internal}"

readonly root_cert="${STEPPATH}/certs/root_ca.crt"
readonly provisioner_password="${STEPPATH}/secrets/password"
readonly backend_dir="/credentials/backend"
readonly mtls_dir="/credentials/zenoh-mtls"
readonly app_dir="/credentials/zenoh-app"
readonly issuer_dir="/credentials/issuer"

for directory in "${backend_dir}" "${mtls_dir}" "${app_dir}" "${issuer_dir}"; do
  mkdir -p "${directory}"
done
chmod 0700 "${backend_dir}" "${mtls_dir}" "${app_dir}" "${issuer_dir}"
install -m 0600 "${provisioner_password}" "${issuer_dir}/provisioner-password"

needs_refresh() {
  local certificate="$1"
  [[ ! -r "${certificate}" ]] || step certificate needs-renewal \
    --expires-in "${SERVICE_CERT_RENEW_WITHIN}" "${certificate}" >/dev/null 2>&1
}

certificate_covers_requested_sans() {
  local certificate="$1"
  shift
  local inspection
  inspection="$(step certificate inspect "${certificate}")" || return 1

  local expect_san=false
  local argument
  for argument in "$@"; do
    if [[ "${expect_san}" == true ]]; then
      grep -Fq -- "${argument}" <<<"${inspection}" || return 1
      expect_san=false
    elif [[ "${argument}" == "--san" ]]; then
      expect_san=true
    fi
  done
  [[ "${expect_san}" == false ]]
}

write_identity() {
  local directory="$1"
  local certificate_name="$2"
  local key_name="$3"
  local common_name="$4"
  shift 4
  local requested_args=("$@")

  local current="${directory}/current"
  if [[ -L "${current}" ]] \
    && ! needs_refresh "${current}/${certificate_name}" \
    && certificate_covers_requested_sans "${current}/${certificate_name}" "${requested_args[@]}" \
    && [[ -r "${current}/${key_name}" ]]; then
    install -m 0644 "${root_cert}" "${directory}/root_ca.pem"
    return
  fi

  local version="$(date +%Y%m%d%H%M%S)-$$"
  local staged="${directory}/.new-${version}"
  mkdir -m 0700 "${staged}"
  step ca certificate \
    --provisioner-password-file "${provisioner_password}" \
    --ca-url "${STEP_CA_URL}" \
    --root "${root_cert}" \
    "$@" "${common_name}" \
    "${staged}/${certificate_name}" "${staged}/${key_name}"
  chmod 0600 "${staged}/${key_name}"
  chmod 0644 "${staged}/${certificate_name}"
  install -m 0644 "${root_cert}" "${staged}/root_ca.pem"
  mkdir -p "${directory}/versions"
  mv "${staged}" "${directory}/versions/${version}"
  ln -s "versions/${version}" "${directory}/.current-${version}"
  mv -Tf "${directory}/.current-${version}" "${current}"
  install -m 0644 "${root_cert}" "${directory}/root_ca.pem"
}

# The private mTLS router identity is also used by the bootstrap router.  Its
# SANs must cover every name clients use to reach either listener.  Keep these
# names deployment-specific; Docker gateway IPs are intentionally not stable
# certificate identities.
router_san_args=()
IFS=',' read -r -a router_sans <<<"${ZENOH_ROUTER_SANS}"
for san in "${router_sans[@]}"; do
  if [[ -n "${san}" ]]; then
    router_san_args+=(--san "${san}")
  fi
done
if [[ ${#router_san_args[@]} -eq 0 ]]; then
  echo "ZENOH_ROUTER_SANS must contain at least one DNS name or IP address" >&2
  exit 1
fi

write_identity "${backend_dir}" "fastapi.crt" "fastapi.key" "Emi Mower Backend" --san localhost
write_identity "${mtls_dir}" "router.crt" "router.key" "Emi Mower Zenoh mTLS" "${router_san_args[@]}"
write_identity "${app_dir}" "router.crt" "router.key" "Emi Mower Zenoh App" --san localhost

touch "${STEPPATH}/credentials-ready"
