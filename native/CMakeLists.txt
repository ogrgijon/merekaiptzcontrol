cmake_minimum_required(VERSION 3.20)
project(merekaiptzcontrol_camera_bridge LANGUAGES CXX)

if(NOT WIN32)
    message(FATAL_ERROR "The USB camera bridge is Windows-only")
endif()

set(CMAKE_MFC_FLAG 2)

add_library(merekaiptzcontrol_camera SHARED
    merekaiptzcontrol_camera_bridge.cpp
    ptzcontrol/ExtensionUnit.cpp
)

target_include_directories(merekaiptzcontrol_camera PRIVATE
    ptzcontrol
)

target_compile_features(merekaiptzcontrol_camera PRIVATE cxx_std_17)
target_compile_definitions(merekaiptzcontrol_camera PRIVATE UNICODE _UNICODE)
target_link_libraries(merekaiptzcontrol_camera PRIVATE strmiids ole32 oleaut32)
set_target_properties(merekaiptzcontrol_camera PROPERTIES OUTPUT_NAME "merekaiptzcontrol_camera")
