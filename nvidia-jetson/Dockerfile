FROM ubuntu:24.04

ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
ENV ROS_DISTRO=jazzy
ENV DEBIAN_FRONTEND=noninteractive

# install locale and basic tools
RUN apt-get update && apt-get install -y \
    locales \
    curl \
    gnupg2 \
    lsb-release \
    software-properties-common \
    && locale-gen en_US en_US.UTF-8 \
    && update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8

RUN add-apt-repository universe && \
    curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/ros2.list > /dev/null

# add the ROS 2 GPG key and repository
RUN curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/ros2.list > /dev/null   

# install ROS 2 Jazzy (Desktop for GUI tools, Base for headless/Jetson)
RUN apt-get update && apt-get install -y \
    ros-jazzy-ros-base \
    ros-dev-tools \
    ros-jazzy-rmw-cyclonedds-cpp \
    && rm -rf /var/lib/apt/lists/*

RUN rosdep init && rosdep update

WORKDIR /jetson

ENV RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

RUN echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc

# default command (to keep docker container alive)
CMD ["bash"]