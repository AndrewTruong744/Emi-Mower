#!/usr/bin/env bash
set -euo pipefail

: "${TPM2TOOLS_TCTI:?TPM2TOOLS_TCTI must name the TPM 2.0 transport}"
: "${TPM_STATE_DIR:=/var/lib/emi-mower/tpm}"
mkdir -p "$TPM_STATE_DIR"

# A newly started swtpm correctly rejects capability queries until TPM2_Startup.
# It is harmless to repeat startup against an already initialized persistent TPM.
tpm2_startup -c >/dev/null 2>&1 || true

for attempt in $(seq 1 30); do
  if tpm2_getcap properties-fixed >/dev/null 2>&1; then
    break
  fi
  if [[ "$attempt" -eq 30 ]]; then
    echo "TPM did not become available" >&2
    exit 1
  fi
  sleep 1
done

handle=0x81000001
if ! tpm2_readpublic -c "$handle" -f pem -o "$TPM_STATE_DIR/device-root-public.pem" >/dev/null 2>&1; then
  # Start from a known transient-object state. This only clears RAM handles;
  # the persistent device-root handle below is unaffected.
  tpm2_flushcontext -t >/dev/null 2>&1 || true
  # The device identity is itself an ECC signing primary. A child key would
  # require holding both parent and child contexts, which exceeds the small
  # swtpm test configuration's context budget during persistence.
  tpm2_createprimary -C o -g sha256 -G ecc \
    -a "fixedtpm|fixedparent|sensitivedataorigin|userwithauth|sign" \
    -c /tmp/emi-device-root.ctx >/dev/null
  tpm2_evictcontrol -C o -c /tmp/emi-device-root.ctx "$handle" >/dev/null
  tpm2_readpublic -c "$handle" -f pem -o "$TPM_STATE_DIR/device-root-public.pem" >/dev/null
fi
chmod 0644 "$TPM_STATE_DIR/device-root-public.pem"
echo "TPM device-root key ready at $TPM_STATE_DIR/device-root-public.pem"
