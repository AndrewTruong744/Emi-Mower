#!/usr/bin/env sh
set -eu

# Requires Node.js and the AsyncAPI CLI:
#   npm install --global @asyncapi/cli
#
# The generated output is committed so backend and app builds do not need the
# AsyncAPI CLI. Re-run this script whenever zenoh_asyncapi.yaml changes.

script_dir=$(CDPATH= cd "$(dirname "$0")" && pwd)
backend_dir=$(CDPATH= cd "${script_dir}/.." && pwd)
cd "$backend_dir"

asyncapi generate models python zenoh_asyncapi.yaml \
  --pyDantic \
  --packageName=emi_mower_zenoh \
  --no-interactive \
  --save-output src/zenoh/generated/types.py

asyncapi generate models typescript zenoh_asyncapi.yaml \
  --tsModelType interface \
  --tsExportType named \
  --no-interactive \
  --save-output ../app/src/generated/zenoh.ts

node tools/generate_zenoh_paths.mjs
node tools/generate_rust_zenoh_types.mjs
