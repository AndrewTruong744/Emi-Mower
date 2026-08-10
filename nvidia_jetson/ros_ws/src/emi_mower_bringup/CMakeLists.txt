cmake_minimum_required(VERSION 3.8)
project(emi_mower_bringup)

find_package(ament_cmake REQUIRED)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_bringup_config test/test_bringup_config.py)
endif()

install(
  DIRECTORY launch config
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
