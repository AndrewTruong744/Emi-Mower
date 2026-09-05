cmake_minimum_required(VERSION 3.8)
project(emi_mower_bringup)

find_package(ament_cmake REQUIRED)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_bringup_config test/test_bringup_config.py)
  ament_add_pytest_test(test_boundary_cutout_node test/test_boundary_cutout_node.py)
endif()

install(
  PROGRAMS emi_mower_bringup/boundary_cutout_node.py
  DESTINATION lib/${PROJECT_NAME}
)

install(
  DIRECTORY emi_mower_bringup
  DESTINATION lib/python3.12/site-packages
)

install(
  DIRECTORY launch config
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
