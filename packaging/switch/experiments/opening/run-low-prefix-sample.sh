#!/bin/sh
# Capture two independent CPU samples with different periods on the retained candidate.
set -eu
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/opening-low-prefix-sample
mkdir -p "$d/hdd"
python3 "$p/wide-motion.py" --serial --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --low-prefix-sample --frame-pc --page-operands
trap 'rm -f "$d/host/replay"' EXIT
nm -nS --defined-only "$d/host/replay" | awk '$3 ~ /^[tTwW]$/ {print}' > "$d/symbols.txt"
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json
export NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
for i in 1 2; do
 if [ "$i" = 2 ] || [ "$i" = 4 ]; then export NGB_PC_REPEAT=1; else unset NGB_PC_REPEAT; fi
 "$d/host/replay" --start-button game_files "$d/hdd" > "$d/run-$i.log" 2>&1 || :
 grep -qF '[RESULT] status=1 reason=verified 120 original demo frames' "$d/run-$i.log"
 grep -F '[FRAME_PC_COUNT]' "$d/run-$i.log"
done
python3 "$p/low-prefix-report.py"
