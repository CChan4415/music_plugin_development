cmake_minimum_required(VERSION 3.22)
project(MyPlugin VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(APPLE)
    set(CMAKE_OSX_DEPLOYMENT_TARGET "10.13" CACHE STRING "")
elseif(WIN32)
    set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
endif()

add_library(MyPlugin STATIC plugin.cpp)
target_include_directories(MyPlugin PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_compile_options(MyPlugin PRIVATE
    $<$<CXX_COMPILER_ID:MSVC>:/W4 /permissive->
    $<$<NOT:$<CXX_COMPILER_ID:MSVC>>:-Wall -Wextra -Wpedantic -Werror>)

enable_testing()
add_executable(plugin_test plugin.cpp)
target_link_libraries(plugin_test PRIVATE MyPlugin)
add_test(NAME smoke COMMAND plugin_test)
