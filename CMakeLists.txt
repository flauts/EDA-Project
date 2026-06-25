cmake_minimum_required(VERSION 3.15)
project(eda_bst_benchmark CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE Release)
endif()


include_directories(${CMAKE_SOURCE_DIR}/src)

add_executable(benchmark src/benchmark.cpp)
add_executable(trees_test src/trees_test.cpp)

enable_testing()
add_test(NAME trees_test COMMAND trees_test)
