## Setup

### Nvidia jetson setup
- install NVIDIA Jetpack iso
- use balena etcher to transfer image to usb

### ROS Jazzy Docker

Run the workspace in the supplied container rather than installing ROS on the
Jetson host. The image is ARM64-compatible and also builds on an ARM64
development computer. It is a **Zenoh client only**: it never starts a router.

For local simulation, start the backend (including its host-networked Zenoh
router) separately, then start ROS:

```bash
cd backend
docker compose -f local-docker-compose.yml up -d zenoh-mtls zenoh-app backend

cd ../nvidia_jetson
# .env must contain the mower UUID. Start from .env.example for simulation,
# or have backend provisioning write it together with certs/.
docker compose up --build
```

The default Compose stack runs `sim.launch.py` and reaches the host router at
`tls/host.docker.internal:7448`. `extra_hosts` supplies that name on Linux as
well as Docker Desktop. Set `ZENOH_ROUTER_ENDPOINT` if the router differs.
`ZENOH_VERIFY_NAME_ON_CONNECT=false` is only the local-development default
because the existing local router certificate names `localhost`; use a router
certificate with the production DNS name and set it to `true` in deployment.

For a physical Jetson, use the override. It builds the OAK-D and SLLidar
drivers, exposes USB and lidar devices, shares the host CAN interface, and
starts `real.launch.py`:

```bash
cd nvidia_jetson
docker compose -f docker-compose.yml -f docker-compose.jetson.yml up --build -d
```

Set `STM32_CAN_INTERFACE` and `RPLIDAR_DEVICE` if the host interfaces differ.
Configure the host CAN interface before starting Compose, for example:

```bash
sudo ip link set can0 up type can bitrate 500000
```

Do not
put the certificate directory in the image or repository; Compose mounts it
read-only at `/etc/mower/certs`.

### Provision a mower

Do not generate mower certificates on the Jetson. On the trusted backend or
factory host, run `backend/src/scripts/provision_mower.py` (documented in
`backend/README.md`). It creates the mower UUID and database record, installs
the matching Zenoh mTLS ACL, issues `mower.crt`, `mower.key`, and
`root_ca.pem`, and writes this directory's ignored `.env` file. The Jetson
never receives the CA private key.

For a simulation-only checkout, copy `.env.example` to `.env` and place a
development certificate bundle in `certs/`. `docker-compose.yml` uses
`env_file: .env`, so its Rust gateway and Python LiveKit node receive the
same `MOWER_ID`.

If the external router is temporarily down, `rmw_zenoh_cpp` cannot initialize a
ROS context. The launch files respawn affected nodes every two seconds until it
can. Once initialized, `zenoh_gateway` reconnects to its native Zenoh routes
with exponential backoff (2–30 seconds). It translates joystick commands to
`/teleop/cmd_vel` and publishes typed `/mower/telemetry` batches on the
AsyncAPI telemetry route. The LiveKit node separately retries its token
session.

### OAKD S2 and Slamtex Lidar S2 installation
- The DepthAI and SLLIDAR ROS 2 drivers are Git submodules. From the repository
  root, import them before building the workspace:
  ```bash
  git submodule update --init --recursive
  ```
  For a fresh clone, use `git clone --recurse-submodules <repo-url>` instead.
  The packages are checked out to `ros_ws/src/depthai-ros` and
  `ros_ws/src/sllidar_ros2`.

### OAKD S2 setup
- cd ~/ros_ws
- rosdep install --from-paths src --ignore-src -r -y
- colcon build --symlink-install
- source install/setup.bash

## Slamtec Lidar S2
cd ~/ros_ws
colcon build --symlink-install
source install/setup.bash
cd ~/ros_ws/src/sllidar_ros2/scripts
sudo chmod +x create_udev_rules.sh
./create_udev_rules.sh


## To run without Docker

After building and sourcing the workspace, use either:

```bash
ros2 launch emi_mower_bringup sim.launch.py mower_id:=mower-01
ros2 launch emi_mower_bringup real.launch.py mower_id:=mower-01
```

The launch file starts the OAK-D S2 RGB stream on `/oak/rgb/image_raw`, the
RPLIDAR S2, and the LiveKit upload node. Pass a different `mower_id` for each
mower so the node requests its token on `mower/{mower_id}/livekit/upload`.

The ROS graph and Python LiveKit node use the same Zenoh 1.9 session
configuration. `rmw_zenoh_cpp` reads `ZENOH_SESSION_CONFIG_URI`; Zenoh-Python
reads `ZENOH_CONFIG`. Docker renders both from the external router endpoint at
container startup. The Rust package pins its Zenoh crate to the same 1.9.0
baseline.

### Local Rust tooling

Install Rust with `rustup` on a development computer even when ROS itself runs
in Docker. This provides fast formatting and basic editor support. Match the
container's Rust 1.88.0 toolchain, and install the formatter and linter:

```bash
# macOS only, if Xcode Command Line Tools are not already installed:
xcode-select --install

curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"
rustup toolchain install 1.88.0
rustup default 1.88.0
rustup component add rustfmt clippy
```

Local formatting does not require ROS:

```bash
cargo fmt --manifest-path ros_ws/src/emi_mower_control/Cargo.toml --check
cargo fmt --manifest-path ros_ws/src/emi_mower_zenoh_gateway/Cargo.toml --check
```

`cargo check`, Clippy, and Rust tests for ROS packages need the Linux ROS
environment, so run them in the supplied container rather than relying on a
macOS host.

### One-command ROS tests

Run all offline ROS Python tests and Rust integration tests with:

```bash
cd nvidia_jetson
./scripts/test.sh
```

The first run builds `emi-mower-ros-test:jazzy`; later runs reuse Docker
volumes for Colcon and Cargo outputs. The test image contains ROS Jazzy, the
Rust compiler, and test dependencies, but it does **not** copy `ros_ws` or
prebuild the workspace. Compose bind-mounts your checkout at runtime, so an
edit to a test or source file does not rebuild the image. The suite is offline:
it does not start Zenoh, access a camera, or open the STM32 CAN interface.

The launcher performs the equivalent of:

```bash
colcon build --packages-select emi_mower_interfaces emi_mower_control emi_mower_zenoh_gateway emi_mower_livekit
python3 -m pytest ros_ws/src/emi_mower_interfaces/test ros_ws/src/emi_mower_bringup/test ros_ws/src/emi_mower_livekit/test ros_ws/src/emi_mower_control/test
cargo test --manifest-path ros_ws/src/emi_mower_control/Cargo.toml
cargo test --manifest-path ros_ws/src/emi_mower_zenoh_gateway/Cargo.toml
```

To inspect the test image without running tests:

```bash
docker compose -f docker-compose.test.yml build ros-test
```

### Rust formatting, error checks, and linting

Run these inside the test image so that `rclrs` and generated ROS messages are
available:

```bash
cd nvidia_jetson
docker compose -f docker-compose.test.yml run --rm --entrypoint bash ros-test -lc '
  source /opt/ros/jazzy/setup.bash
  cargo fmt --manifest-path /ws/src/emi_mower_control/Cargo.toml --check
  cargo fmt --manifest-path /ws/src/emi_mower_zenoh_gateway/Cargo.toml --check
  cargo check --manifest-path /ws/src/emi_mower_control/Cargo.toml
  cargo check --manifest-path /ws/src/emi_mower_zenoh_gateway/Cargo.toml
  cargo clippy --manifest-path /ws/src/emi_mower_control/Cargo.toml --all-targets -- -D warnings
  cargo clippy --manifest-path /ws/src/emi_mower_zenoh_gateway/Cargo.toml --all-targets -- -D warnings
'
```
