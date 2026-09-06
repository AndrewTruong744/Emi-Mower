#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: issue_mower_certificate.sh --mower-id UUID --output-dir DIRECTORY \
  [--csr PATH] [--ca-cert PATH] [--ca-key PATH] [--ca-key-passphrase-file PATH]

Issue a unique mTLS client certificate for a provisioned mower. Run this only
on a trusted provisioning host that holds the CA private key.
EOF
}

mower_id=""
output_dir=""
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
backend_dir="$(cd "${script_dir}/.." && pwd)"
ca_cert="${backend_dir}/certs/ca/ca.crt"
ca_key="${backend_dir}/certs/ca/ca.key"
ca_key_passphrase_file=""
csr_path=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mower-id)
      mower_id="${2:-}"
      shift 2
      ;;
    --output-dir)
      output_dir="${2:-}"
      shift 2
      ;;
    --ca-cert)
      ca_cert="${2:-}"
      shift 2
      ;;
    --ca-key)
      ca_key="${2:-}"
      shift 2
      ;;
    --ca-key-passphrase-file)
      ca_key_passphrase_file="${2:-}"
      shift 2
      ;;
    --csr)
      csr_path="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ ! "$mower_id" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$ ]]; then
  echo "--mower-id must be a UUID" >&2
  exit 2
fi
if [[ -z "$output_dir" ]]; then
  echo "--output-dir is required" >&2
  exit 2
fi
if [[ ! -r "$ca_cert" || ! -r "$ca_key" ]]; then
  echo "CA certificate or private key is not readable" >&2
  exit 1
fi
if [[ -n "$ca_key_passphrase_file" && ! -r "$ca_key_passphrase_file" ]]; then
  echo "CA key passphrase file is not readable" >&2
  exit 1
fi
if [[ -n "$csr_path" && ! -r "$csr_path" ]]; then
  echo "CSR is not readable" >&2
  exit 1
fi

umask 077
mkdir -p "$output_dir"

cert_path="${output_dir}/mower.crt"
key_path="${output_dir}/mower.key"
ca_output_path="${output_dir}/root_ca.pem"
if [[ -e "$cert_path" || -e "$key_path" ]]; then
  certificate_subject=""
  if [[ -r "$cert_path" ]]; then
    certificate_subject="$(openssl x509 -in "$cert_path" -noout -subject -nameopt RFC2253)"
  fi
  if [[ -r "$cert_path" && -r "$key_path" ]] \
    && [[ "$certificate_subject" == "subject=CN=mower:${mower_id},O=EmiSamaTechnologies,C=US" ]]; then
    cp "$ca_cert" "$ca_output_path"
    chmod 0600 "$key_path"
    chmod 0644 "$cert_path" "$ca_output_path"
    echo "Reused existing mower certificate for ${mower_id}"
    exit 0
  fi
  echo "certificate output already exists but does not match mower ${mower_id}" >&2
  exit 1
fi

temporary_dir="$(mktemp -d "${output_dir}/.issue.XXXXXX")"
trap 'rm -rf "$temporary_dir"' EXIT
config_path="${temporary_dir}/mower.cnf"

cat > "$config_path" <<EOF
[req]
prompt = no
default_bits = 2048
default_md = sha256
distinguished_name = dn
req_extensions = req_ext

[dn]
C = US
O = EmiSamaTechnologies
CN = mower:${mower_id}

[req_ext]
extendedKeyUsage = clientAuth
EOF

if [[ -n "$csr_path" ]]; then
  cp "$csr_path" "${temporary_dir}/mower.csr"
  csr_subject="$(openssl req -in "${temporary_dir}/mower.csr" -noout -subject -nameopt RFC2253)"
  if [[ "$csr_subject" != "subject=CN=mower:${mower_id},O=EmiSamaTechnologies,C=US" ]]; then
    echo "CSR subject must be CN=mower:${mower_id}" >&2
    exit 1
  fi
else
  openssl genrsa -out "${temporary_dir}/mower.key" 2048
  openssl req -new \
    -key "${temporary_dir}/mower.key" \
    -out "${temporary_dir}/mower.csr" \
    -config "$config_path"
fi
x509_args=(
  -req
  -in "${temporary_dir}/mower.csr"
  -CA "$ca_cert"
  -CAkey "$ca_key"
  -CAcreateserial
  -out "${temporary_dir}/mower.crt"
  -days 90
  -sha256
  -extfile "$config_path"
  -extensions req_ext
)
if [[ -n "$ca_key_passphrase_file" ]]; then
  x509_args+=( -passin "file:${ca_key_passphrase_file}" )
fi
openssl x509 "${x509_args[@]}"

if [[ -n "$csr_path" ]]; then
  # The mower owns the operational private key used for this CSR. Never copy
  # a private key from the issuer into a renewal bundle.
  :
else
  mv "${temporary_dir}/mower.key" "$key_path"
fi
mv "${temporary_dir}/mower.crt" "$cert_path"
cp "$ca_cert" "$ca_output_path"
if [[ -n "$csr_path" ]]; then
  rm -f "$key_path"
else
  chmod 0600 "$key_path"
fi
chmod 0644 "$cert_path" "$ca_output_path"

echo "Issued mower mTLS certificate for ${mower_id} in ${output_dir}"
