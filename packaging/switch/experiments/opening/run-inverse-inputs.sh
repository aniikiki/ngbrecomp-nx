#!/bin/sh
set -eu
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/opening-inverse-inputs
mkdir -p "$d/hdd"
python3 "$p/wide-motion.py" --serial --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --entry-stream --guest-sites --inverse-inputs
trap 'rm -f "$d/host/replay"' EXIT
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
"$d/host/replay" --start-button game_files "$d/hdd" > "$d/budget.log" 2>&1 || :
grep -Fq 'verified 120 original demo frames' "$d/budget.log"
grep -F '[INVERSE_INPUTS]' "$d/budget.log"
