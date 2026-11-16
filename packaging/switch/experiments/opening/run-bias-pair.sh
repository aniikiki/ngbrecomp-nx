#!/bin/sh
set -eu
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/opening-shader-child


python3 "$p/wide-motion.py" --serial --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --tree-pair-cost --shader-child --select-split --bias-pair
trap 'rm -f "$d/host/replay"' EXIT
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
"$d/host/replay" --start-button game_files build/switch-runtime/core-perf/opening-present-combined/hdd > "$d/bias-pair.log" 2>&1 || :
grep -Fq 'verified 120 original demo frames' "$d/bias-pair.log"
grep -F '[BIAS_PAIR]' "$d/bias-pair.log"
