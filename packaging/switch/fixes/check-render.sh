#!/bin/sh
set -eu
cd "$(dirname "$0")/../../.."
docker run --rm -v "$PWD:/work:ro" -w /work -e EGL_PLATFORM=surfaceless \
  -e LIBGL_ALWAYS_SOFTWARE=1 ngb-switch-host:direct0331 sh -ec '
  gl=build/switch-runtime/direct/glslang-host/glslang
  c++ -std=c++20 -O1 -ffunction-sections -fdata-sections -Isrc/d3d \
    packaging/switch/fixes/render.cpp src/d3d/gpu/shaders.cpp src/d3d/vk/spirv.cpp \
    -Ibuild/switch-runtime/opt032/vulkan/glslang-16.0.0 "$gl/libglslang.a" "$gl/libglslang-default-resource-limits.a" -Wl,--gc-sections \
    -lEGL -lGLESv2 -o /tmp/render
  /tmp/render'
