## Setup

### Nvidia jetson setup
- install NVIDIA Jetpack iso
- use balena etcher to transfer image to usb

### ros installation
- sudo apt update && sudo apt install locales -y
- sudo locale-gen en_US en_US.UTF-8
- sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
- export LANG=en_US.UTF-8
- sudo apt install software-properties-common -y
- sudo add-apt-repository universe -y
- sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
- echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
- sudo apt update && sudo apt upgrade -y
- sudo apt install ros-jazzy-desktop ros-jazzy-rmw-zenoh-cpp ros-dev-tools python3-colcon-common-extensions -y

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

## To run
- source /opt/ros/jazzy/setup.bash
- ros2 launch emi_mower_bringup launch_all_nodes.py mower_id:=mower-01

The launch file starts the OAK-D S2 RGB stream on `/oak/rgb/image_raw`, the
RPLIDAR S2, and the LiveKit upload node. Pass a different `mower_id` for each
mower so the node requests its token on `mower/{mower_id}/livekit/upload`.

The ROS graph and the Python LiveKit node use the same Zenoh 1.9 session
configuration. `rmw_zenoh_cpp` reads `ZENOH_SESSION_CONFIG_URI`; Zenoh-Python
reads `ZENOH_CONFIG`. The bringup launch file sets both to
`config/zenoh_client.json5`, which connects to the backend
`zenoh-router-mtls` listener on TLS port 7448. Install the mower certificate,
private key, and backend CA at the paths in that file before running the
launch. The Rust package pins its Zenoh crate to the same 1.9.0 baseline.
