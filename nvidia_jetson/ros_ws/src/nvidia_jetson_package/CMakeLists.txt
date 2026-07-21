cmake_minimum_required(VERSION 3.8)
project(nvidia_jetson_package)

# 1. Load mandatory build engines
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rclpy REQUIRED)
find_package(std_msgs REQUIRED)

# ==============================================================================
# PYTHON INSTALLATION SECTION
# ==============================================================================

# 2. Expose internal helper modules (ros_subscribers.py, mqtt_listeners.py)
# This points directly to the nested directory named 'nvidia_jetson_package/'
ament_python_install_package(${PROJECT_NAME})

# 3. Expose executable nodes to 'ros2 run'
# Makes mqtt_node.py executable by installing it into lib/nvidia_jetson_package/
install(PROGRAMS
  scripts/mqtt_node.py
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY launch
  DESTINATION share/${PROJECT_NAME}/
)

# ==============================================================================
# FINAL BUILD REGISTRATION
# ==============================================================================
ament_package()