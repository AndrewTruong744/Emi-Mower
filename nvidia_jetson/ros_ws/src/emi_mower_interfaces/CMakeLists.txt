cmake_minimum_required(VERSION 3.8)
project(emi_mower_interfaces)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/MowerState.msg"
  "msg/TelemetryRecord.msg"
  "msg/TelemetryBatch.msg"
  DEPENDENCIES std_msgs
)

ament_export_dependencies(rosidl_default_runtime)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_telemetry_interfaces test/test_telemetry_interfaces.py)
endif()

ament_package()
