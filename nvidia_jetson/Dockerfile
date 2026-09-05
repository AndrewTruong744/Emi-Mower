FROM ros:jazzy-ros-base-noble

ARG BUILD_PHYSICAL_DRIVERS=0
ENV DEBIAN_FRONTEND=noninteractive
ENV ROS_DISTRO=jazzy
ENV PATH=/root/.cargo/bin:${PATH}
WORKDIR /ws

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        gettext-base \
        git \
        libclang-dev \
        libudev-dev \
        pkg-config \
        procps \
        python3-colcon-common-extensions \
        python3-pip \
        ros-jazzy-ament-cmake-pytest \
        ros-jazzy-example-interfaces \
        ros-jazzy-rmw-zenoh-cpp \
        ros-jazzy-test-msgs \
        ros-dev-tools \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal --default-toolchain 1.88.0
RUN rustup component add rustfmt clippy
RUN python3 -m pip install --no-cache-dir --break-system-packages \
        cargo-ament-build \
        colcon-cargo \
        colcon-ros-cargo \
        pytest \
    && python3 -m pip install --no-cache-dir --break-system-packages -r /tmp/requirements.txt

COPY ros_ws/src /ws/src
COPY docker/zenoh_client.json5.in /opt/emi-mower/zenoh_client.json5.in

RUN rosdep init 2>/dev/null || true
RUN rosdep update \
    && rosdep install --from-paths \
        src/emi_mower_interfaces \
        src/emi_mower_livekit \
        src/emi_mower_control \
        src/emi_mower_zenoh_gateway \
        --ignore-src --rosdistro jazzy -r -y \
        --skip-keys "ament_cargo ament_python depthai_ros_driver rclrs sllidar_ros2"

# The simulator image deliberately excludes the OAK-D and lidar drivers. The
# Jetson Compose override sets BUILD_PHYSICAL_DRIVERS=1 and builds them.
# ament_cargo leaves Cargo intermediates beside the source. They are only useful
# while compiling; installed executables remain in /ws/install.
RUN . /opt/ros/${ROS_DISTRO}/setup.sh \
    && if [ "${BUILD_PHYSICAL_DRIVERS}" = "1" ]; then \
         git clone --depth 1 --branch kilted https://github.com/luxonis/depthai-core.git src/depthai-core \
         && git -C src/depthai-core submodule update --init --recursive \
         && colcon build --merge-install --symlink-install; \
       else \
         colcon build --merge-install --symlink-install --packages-select \
           emi_mower_interfaces emi_mower_control emi_mower_zenoh_gateway emi_mower_livekit emi_mower_bringup; \
       fi \
    && find /ws/src -type d -name target -prune -exec rm -rf {} +

COPY docker/ros-entrypoint.sh /usr/local/bin/ros-entrypoint.sh
RUN chmod 0755 /usr/local/bin/ros-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/ros-entrypoint.sh"]
CMD ["bash", "-lc", ": \"${MOWER_ID:?set MOWER_ID in the provisioned container environment}\"; if [ \"${MOWER_LAUNCH:-sim}\" = real ]; then ros2 launch emi_mower_bringup real.launch.py mower_id:=${MOWER_ID}; else ros2 launch /ws/src/emi_mower_bringup/launch/sim.launch.py mower_id:=${MOWER_ID}; fi"]
