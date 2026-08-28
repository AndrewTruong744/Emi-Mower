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
# certs/ must contain mower.crt, mower.key, and root_ca.pem.
# For local development, root_ca.pem is backend/certs/ca/ca.crt.
docker compose up --build
```

The default Compose stack runs `sim.launch.py` and reaches the host router at
`tls/host.docker.internal:7448`. `extra_hosts` supplies that name on Linux as
well as Docker Desktop. Set `ZENOH_ROUTER_ENDPOINT` if the router differs.
`ZENOH_VERIFY_NAME_ON_CONNECT=false` is only the local-development default
because the existing local router certificate names `localhost`; use a router
certificate with the production DNS name and set it to `true` in deployment.

For a physical Jetson, use the override. It builds the OAK-D and SLLidar
drivers, exposes USB, lidar, and UART devices, and starts `real.launch.py`:

```bash
cd nvidia_jetson
MOWER_CERT_DIR=/opt/emi-mower/certs \
ZENOH_ROUTER_ENDPOINT=tls/zenoh.example.internal:7448 \
docker compose -f docker-compose.yml -f docker-compose.jetson.yml up --build -d
```

Set `STM32_UART_DEVICE` and `RPLIDAR_DEVICE` if the udev paths differ. Do not
put the certificate directory in the image or repository; Compose mounts it
read-only at `/etc/mower/certs`.

If the external router is temporarily down, `rmw_zenoh_cpp` cannot initialize a
ROS context. The launch files respawn affected nodes every two seconds until it
can. Once initialized, `teleop_gateway` also reconnects to its native Zenoh
joystick subscription with exponential backoff (2–30 seconds), and the LiveKit
node retries its token session.

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


## Mower key (in mower)
- For each mower you want to register, run the script "generate_mower_cert" and then setup the mower

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
