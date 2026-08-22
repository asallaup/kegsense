cmake_minimum_required(VERSION 3.12.4)
project(kegstation_sim C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Point LVGL at our lv_conf.h explicitly, rather than relying on its
# "next to the lvgl folder" default-location convention.
set(LV_BUILD_CONF_PATH "${CMAKE_CURRENT_SOURCE_DIR}/lv_conf.h" CACHE PATH "" FORCE)

# Derives CONFIG_LV_USE_SDL (etc.) from lv_conf.h -- without this, LVGL's
# own CMake never wires up the SDL2 include/link flags for its SDL driver
# files, even though LV_USE_SDL is enabled in lv_conf.h.
set(LV_BUILD_SET_CONFIG_OPTS ON CACHE BOOL "" FORCE)

# Skeleton project -- skip LVGL's bundled demos/examples to keep the
# build fast and the dependency footprint (ThorVG, OpenGL, etc.) minimal.
set(CONFIG_LV_BUILD_DEMOS OFF CACHE BOOL "" FORCE)
set(CONFIG_LV_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(CONFIG_LV_USE_THORVG_INTERNAL OFF CACHE BOOL "" FORCE)

add_subdirectory(extern/lvgl)

find_package(SDL2 REQUIRED)

add_executable(kegstation_sim
    src/main.c
    src/ui.c
)

target_link_libraries(kegstation_sim PRIVATE lvgl ${SDL2_LIBRARIES})
target_include_directories(kegstation_sim PRIVATE ${SDL2_INCLUDE_DIRS})
