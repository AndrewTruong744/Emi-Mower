cmake_minimum_required(VERSION 3.8)
project(emi_mower_rust)

find_package(ament_cmake REQUIRED)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_cargo_manifest test/test_cargo_manifest.py)
endif()

ament_package()
