cmake_minimum_required(VERSION 3.15...3.27)
project(airo_tulipy)

if (CMAKE_VERSION VERSION_LESS 3.18)
    set(DEV_MODULE Development)
else()
    set(DEV_MODULE Development.Module)
endif()

find_package(Python 3.10 COMPONENTS Interpreter ${DEV_MODULE} REQUIRED)

# Release build by default to avoid large binaries and slow binding code.
if (NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Choose the type of build." FORCE)
    set_property(CACHE CMAKE_BUILD_TYPE PROPERTY STRINGS "Debug" "Release" "MinSizeRel" "RelWithDebInfo")
endif()

# Detect the installed nanobind package and import it into CMake.
# Assumes you've installed nanobind via pip or conda.
execute_process(
        COMMAND "${Python_EXECUTABLE}" -m nanobind --cmake_dir
        OUTPUT_STRIP_TRAILING_WHITESPACE OUTPUT_VARIABLE NB_DIR)
list(APPEND CMAKE_PREFIX_PATH "${NB_DIR}")
find_package(nanobind CONFIG REQUIRED)

find_package(Boost REQUIRED COMPONENTS thread)

include_directories(
    include
    include/kelo_tulip/soem
    include/kelo_tulip/soem/osal
    include/kelo_tulip/soem/osal/linux
    include/kelo_tulip/soem/oshw/linux
)

# Optionally apply cap_net_raw+ep permissions to binary. Requires root privileges.
# Use sudo as default. Still, allow to be configured as environment variable.
OPTION(USE_SETCAP "Set permissions to access ethernet interface without sudo" ON)
IF("$ENV{SUDO_COMMAND}" STREQUAL "")
    SET(SUDO_COMMAND sudo)				# default = sudo
ELSE("$ENV{SUDO_COMMAND}" STREQUAL "")
    SET(SUDO_COMMAND $ENV{SUDO_COMMAND})
ENDIF("$ENV{SUDO_COMMAND}" STREQUAL "")

add_subdirectory(src/kelo_tulip/soem)

nanobind_add_module(tulipy src/tulipy.cpp)

target_link_libraries(tulipy
        PRIVATE
    ${Boost_LIBRARIES}
    soem
    pthread
)

IF(USE_SETCAP)
    add_custom_command(TARGET tulipy POST_BUILD
        COMMAND ${SUDO_COMMAND} setcap cap_net_raw+ep $<TARGET_FILE:tulipy>
    )
endif(USE_SETCAP)