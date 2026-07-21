## Setup

- install NVIDIA Jetpack iso
- use balena etcher to transfer image to usb

- sudo apt update && sudo apt install locales -y
- sudo locale-gen en_US en_US.UTF-8
- sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
- export LANG=en_US.UTF-8
- sudo apt install software-properties-common -y
- sudo add-apt-repository universe -y
- sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
- echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
- sudo apt update && sudo apt upgrade -y
- sudo apt install ros-jazzy-desktop ros-dev-tools python3-colcon-common-extensions -y

- source /opt/ros/jazzy/setup.bash
- cd into ros_ws
- sudo apt install python3.12-venv
- python3 -m venv --system-site-packages .venv
- source .venv/bin/activate

- colcon build --symlink-install
- rosdep update


## Mower key (in mower)
- For each mower you want to register, run the script "generate_mower_cert" and then setup the mower

## To run
- source /opt/ros/jazzy/setup.bash
- ros2 run nvidia_jetson_package launch_all_nodes.py