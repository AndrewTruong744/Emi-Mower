#!/usr/bin/env sh
set -eu

# Requires Node.js and the AsyncAPI CLI:
#   npm install --global @asyncapi/cli
#
# The generated output is committed so backend and app builds do not need the
# AsyncAPI CLI. Re-run this script whenever zenoh_asyncapi.yaml changes.

asyncapi generate models python zenoh_asyncapi.yaml \
  --pyDantic \
  --save-output src/zenoh/generated/types.py

asyncapi generate models typescript zenoh_asyncapi.yaml \
  --tsModelType interface \
  --tsExportType named \
  --save-output ../app/src/generated/zenoh.ts

node scripts/generate_zenoh_paths.mjs
