#!/usr/bin/env bash
# Private startup build: includes code/data generated from the user's XBE.
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
image=${SWITCH_IMAGE:-devkitpro/devkita64@sha256:1fc388c3a0d34bd2045a6dadcb1020e069d5f876a187fd705de14b4440c00282}
target=${1:-switch}
checks=0
case "$target" in
    host|switch) ;;
    check) target=host; checks=1 ;;
    *) echo "usage: $0 [host|switch|check] [--generate]" >&2; exit 2 ;;
esac
out="$root/build/switch-runtime"
xbe="$root/game_files/default.xbe"
mkdir -p "$out"
if [ ! -f "$xbe" ]; then
    bash "$root/tools/pipeline.sh" "${NGB_ISO:-$root/disc/Ninja Gaiden Black.iso}" > "$out/pipeline.log" 2>&1
fi
hash=$(shasum -a 256 "$xbe" | cut -d ' ' -f 1)
previous=$(cat "$out/gen-raw/input.sha256" 2>/dev/null || true)
if [ "${2:-}" = --generate ] || [ "$previous" != "$hash" ] || [ ! -f "$out/gen-raw/recomp_dispatch.c" ]; then
    # Re-run analysis before lifting, including the repository's indirect-call seeds.
    bash "$root/tools/pipeline.sh" "${NGB_ISO:-$root/disc/Ninja Gaiden Black.iso}" > "$out/pipeline.log" 2>&1
    (
        cd "$root/xboxrecomp"
        .venv/bin/python -m tools.recomp "$xbe" --all --split 250 \
            --game-name 'Ninja Gaiden Black Switch bring-up' \
            --gen-dir "$out/gen-raw"
    ) > "$out/generate-runtime.log" 2>&1
    printf '%s\n' "$hash" > "$out/gen-raw/input.sha256"
fi
python3 "$root/packaging/switch/runtime/prepare.py"
if [ ! -f "$root/xboxrecomp/third_party/nv2a_vsh_cpu/src/nv2a_vsh_cpu.c" ] || [ ! -f "$root/xboxrecomp/third_party/xxHash/xxhash.h" ] || [ ! -f "$root/xboxrecomp/third_party/stb/stb_dxt.h" ]; then
    bash "$root/xboxrecomp/third_party/fetch.sh"
fi
if [ "$target" = host ]; then
    python3 "$root/packaging/switch/runtime/stage_disc.py"
    docker build --build-arg "SDK_IMAGE=$image" -t ngb-switch-host:ffmpeg - < "$root/packaging/switch/Dockerfile.host"
    image=ngb-switch-host:ffmpeg
fi
spirv_seed=${NGB_DIRECT_SPIRV:-}
if [ -z "$spirv_seed" ] && [ -f "$out/shader-cache/spirv.bin" ]; then
    spirv_seed=/work/build/switch-runtime/shader-cache/spirv.bin
fi
mounts=()
if [ "${NGB_DIRECT3D:-ON}" = ON ] && [ "$target" = switch ]; then
    mounts+=(-v "${NGB_NXVK_ROOT:-$root/../nxvk}:/nxvk:ro")
fi
docker run "${mounts[@]}" -e "NGB_DIRECT3D=${NGB_DIRECT3D:-ON}" --rm --cpus=4 --memory=6g -v "$root:/work" -w /work \
    -e "NGB_DIRECT_SPIRV=$spirv_seed" -e "NGB_BUILD_TARGET=$target" -e "NGB_RUN_CHECKS=$checks" "$image" bash -eu -c '
    flags=(-DNGB_DIRECT3D="$NGB_DIRECT3D")
    if [ "$NGB_BUILD_TARGET" = switch ]; then
        flags+=(-DNGB_DIRECT_SPIRV="$NGB_DIRECT_SPIRV" -DNGB_NXVK_ROOT=/nxvk -DCMAKE_TOOLCHAIN_FILE=/opt/devkitpro/cmake/Switch.cmake)
    fi
    cmake -S packaging/switch/runtime -B "build/switch-runtime/$NGB_BUILD_TARGET" \
        -G Ninja -DCMAKE_BUILD_TYPE=Release "${flags[@]}"
    cmake --build "build/switch-runtime/$NGB_BUILD_TARGET" -j2
    if [ "$NGB_RUN_CHECKS" = 1 ]; then
        ctest --test-dir build/switch-runtime/host --output-on-failure
        python3 packaging/switch/runtime/verify.py
    fi
    dkp-pacman -Q devkitA64 libnx switch-tools > build/switch-runtime/toolchain.txt
' > "$out/$target-build.log" 2>&1
printf '%s\n' "$image" > "$out/image.txt"
suffix=
if [ "$target" = switch ]; then suffix=.nro; fi
echo "Build complete: $out/$target/ngb-startup$suffix"
