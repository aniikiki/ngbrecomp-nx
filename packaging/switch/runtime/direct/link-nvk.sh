#!/usr/bin/env bash
# The 2D EGL presenter uses the SDK's Mesa. Keep the private symbols of
# nxvk's newer Mesa in its own object before linking the two drivers.
set -euo pipefail
tree=$1
output=$2
sdk=${DEVKITPRO:-/opt/devkitpro}
toolsdir="$sdk/devkitA64/bin/aarch64-none-elf"
cross="$tree/switch/build/cross"
driver="$cross/src/nouveau/vulkan/libnvk.a"
libs=(
  src/util/libmesa_util.a src/util/libmesa_util_simd.a src/util/blake3/libblake3.a
  src/c11/impl/libmesa_util_c11.a
  src/nouveau/compiler/libnak.a src/nouveau/compiler/libnak_rs.a src/compiler/rust/libcompiler_c_helpers.a
  src/nouveau/headers/libnvidia_headers_c.a src/nouveau/nil/libnil.a src/nouveau/nil/liblibnil_format_table.a
  src/compiler/nir/libnir.a src/compiler/libcompiler.a src/nouveau/mme/libnouveau_mme.a
  src/nouveau/winsys/libnouveau_ws.a src/vulkan/util/libvulkan_util.a
  src/compiler/spirv/libvtn.a src/util/libxmlconfig.a
)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
"$toolsdir-gcc" -D__SWITCH__ -fPIE -mtp=soft -ftls-model=local-exec -ffunction-sections -fdata-sections -I"$sdk/libnx/include" -c "$tree/switch/smoke/nvk_compat.c" -o "$tmp/compat.o"
"$toolsdir-ld" -r -u vk_icdGetInstanceProcAddr "$tmp/compat.o" --whole-archive "$driver" --no-whole-archive --start-group "${libs[@]/#/$cross/}" --end-group -o "$tmp/driver.o"
"$toolsdir-nm" --defined-only -g -P "$tmp/driver.o" | awk '$1 != "vk_icdGetInstanceProcAddr" && $2 !~ /^[uU]$/ {print $1}' > "$tmp/private"
"$toolsdir-objcopy" --localize-symbols="$tmp/private" "$tmp/driver.o" "$output"
