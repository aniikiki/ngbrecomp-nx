#!/usr/bin/env bash
# Build a standalone platform probe without generated game code or game assets.
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
image=${SWITCH_IMAGE:-devkitpro/devkita64@sha256:1fc388c3a0d34bd2045a6dadcb1020e069d5f876a187fd705de14b4440c00282}
docker run --rm -v "$root:/work" -w /work "$image" bash -eu -c '
    out=build/switch-probe
    mkdir -p "$out"
    /opt/devkitpro/devkitA64/bin/aarch64-none-elf-gcc \
        -std=gnu11 -O2 -g -Wall -Wextra -Werror \
        -march=armv8-a+crc+crypto -mtune=cortex-a57 -mtp=soft -fPIE \
        -ffunction-sections -fdata-sections -D__SWITCH__ \
        -I/opt/devkitpro/libnx/include \
        -specs=/opt/devkitpro/libnx/switch.specs \
        packaging/switch/probe/main.c \
        -L/opt/devkitpro/libnx/lib -lnx \
        -Wl,-Map,"$out/ngb-basic-probe.map" \
        -o "$out/ngb-basic-probe.elf"
    nacptool --create "NGB Basic Probe" "NGB port development" "0.1.0" "$out/ngb-basic-probe.nacp"
    elf2nro "$out/ngb-basic-probe.elf" "$out/ngb-basic-probe.nro" \
        --nacp="$out/ngb-basic-probe.nacp" --icon=/opt/devkitpro/libnx/default_icon.jpg
    /opt/devkitpro/devkitA64/bin/aarch64-none-elf-readelf -h "$out/ngb-basic-probe.elf"
    dkp-pacman -Q devkitA64 libnx switch-tools > "$out/toolchain.txt"
    sha256sum "$out/ngb-basic-probe.nro"
'
printf '%s\n' "$image" > "$root/build/switch-probe/image.txt"
