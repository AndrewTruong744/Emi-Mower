#!/bin/bash
# Initialize the local development CA once, in step-ca's persistent volume.
set -euo pipefail

: "${STEPPATH:=/home/step}"
readonly root_cert="${STEPPATH}/certs/root_ca.crt"
readonly ca_config="${STEPPATH}/config/ca.json"
readonly password_file="${STEPPATH}/secrets/password"

configure_certificate_lifetime() {
  if grep -q '"maxTLSCertDuration"' "${ca_config}"; then
    return
  fi
  sed -i '/"provisioners": \[/i\		"claims": {"maxTLSCertDuration": "2160h", "defaultTLSCertDuration": "2160h"},' "${ca_config}"
}

if [[ -f "${ca_config}" && -f "${root_cert}" ]]; then
  configure_certificate_lifetime
  exit 0
fi

if [[ -e "${ca_config}" || -e "${root_cert}" ]]; then
  echo "incomplete step-ca state; refusing to overwrite ${STEPPATH}" >&2
  exit 1
fi

umask 077
mkdir -p "${STEPPATH}/secrets"
if [[ ! -s "${password_file}" ]]; then
  set +o pipefail
  tr -dc 'A-Za-z0-9' </dev/urandom | head -c 48 >"${password_file}"
  set -o pipefail
fi

step ca init \
  --name "${STEP_CA_NAME:-Emi Mower Local Development}" \
  --dns "${STEP_CA_DNS_NAMES:-localhost,step-ca}" \
  --address "${STEP_CA_ADDRESS:-:9000}" \
  --provisioner "${STEP_CA_PROVISIONER_NAME:-emi-mower-local}" \
  --password-file "${password_file}" \
  --provisioner-password-file "${password_file}"
configure_certificate_lifetime
