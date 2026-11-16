#!/bin/sh
# Inside the ARM Linux replay image; invocation: sh run-register-pgo.sh base|train|use LOGNAME
set -eu
d=build/switch-runtime/core-perf/opening-register-pgo
case "$1" in train|use|base);;*)exit 2;;esac
mkdir -p "$d/hdd"
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json
export NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
"$d/replay-$1" --start-button build/switch-runtime/romfs "$d/hdd" >"$d/$2.log" 2>&1 || :
grep -Fq '[RESULT] status=1 reason=verified 120 original demo frames' "$d/$2.log"
if [ "$1" = train ]; then grep -Fq '[TRAIN] wrote 14 profiles' "$d/$2.log"; fi
