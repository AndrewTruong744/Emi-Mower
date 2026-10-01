cmake_minimum_required(VERSION 3.8)
project(emi_mower_bringup)

find_package(ament_cmake REQUIRED)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_bringup_config test/test_bringup_config.py)
endif()

install(
  DIRECTORY emi_mower_bringup
  DESTINATION lib/python3.12/site-packages
)

install(
  DIRECTORY launch config
  DESTINATION share/${PROJECT_NAME}
)

install(
  PROGRAMS emi_mower_bringup/sim_bridge.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME sim_bridge
)

ament_package()
