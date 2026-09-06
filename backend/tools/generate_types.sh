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

validation_output=$(mktemp -d)
trap 'rm -rf "$validation_output"' EXIT

# The AsyncAPI CLI emits one file per model. Generate those transiently as a
# schema validation step; the repository's stable aggregate bindings below are
# produced by its checked-in generators.
asyncapi generate models python zenoh_asyncapi.yaml \
  --pyDantic \
  --packageName=emi_mower_zenoh \
  --no-interactive \
  --output "$validation_output/python"

asyncapi generate models typescript zenoh_asyncapi.yaml \
  --tsModelType interface \
  --tsExportType named \
  --no-interactive \
  --output "$validation_output/typescript"

node tools/generate_zenoh_paths.mjs
node tools/generate_rust_zenoh_types.mjs
node tools/generate_renewal_python_types.mjs

# Keep generated Rust source in the form checked by the Jetson build.
if command -v cargo >/dev/null 2>&1; then
  cargo fmt --manifest-path ../nvidia_jetson/ros_ws/src/emi_mower_zenoh_gateway/Cargo.toml
fi
