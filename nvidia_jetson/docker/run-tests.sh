#!/usr/bin/env bash
set -euo pipefail

set +u
source "/opt/ros/${ROS_DISTRO}/setup.bash"
set -u

# Build the small, simulator-safe package set. This generates the custom ROS
# interfaces and makes them available to the Rust bindings before Cargo tests.
colcon build --merge-install --symlink-install --packages-select \
  emi_mower_interfaces \
  emi_mower_control \
  emi_mower_zenoh_gateway \
  emi_mower_livekit

set +u
source /ws/install/setup.bash
set -u

# These are deliberately direct pytest invocations: they are fast, offline
# unit tests and do not need a Zenoh router, camera, or CAN interface.
python3 -m pytest \
  /ws/src/emi_mower_interfaces/test \
  /ws/src/emi_mower_bringup/test \
  /ws/src/emi_mower_livekit/test \
  /ws/src/emi_mower_control/test

cargo test --manifest-path /ws/src/emi_mower_control/Cargo.toml
cargo test --manifest-path /ws/src/emi_mower_zenoh_gateway/Cargo.toml
