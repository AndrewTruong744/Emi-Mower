#!/usr/bin/env bash
set -euo pipefail

mkdir -p /var/lib/swtpm
exec swtpm socket \
  --tpm2 \
  --tpmstate dir=/var/lib/swtpm,mode=0600 \
  --server type=tcp,port=2321,bindaddr=0.0.0.0 \
  --ctrl type=tcp,port=2322,bindaddr=0.0.0.0 \
  --flags not-need-init
