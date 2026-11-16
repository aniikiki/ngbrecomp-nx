#!/bin/sh
set -eu
p=packaging/switch/experiments/opening
name=task298-cost; extra=
if [ "${1:-}" = inner ]; then name=task200-cost; extra=--inner; fi
if [ "${1:-}" = update ]; then name=task2ae-cost; extra=--update; fi
d=build/switch-runtime/core-perf/opening-$name
python3 "$p/task298-cost.py" $extra
python3 "$p/wide-motion.py" --serial --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --tree-pair-cost "--$name"
trap 'rm -f "$d/host/replay"' EXIT
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
"$d/host/replay" --start-button game_files build/switch-runtime/core-perf/opening-present-combined/hdd > "$d/budget.log" 2>&1 || :
grep -Fq 'verified 120 original demo frames' "$d/budget.log"
grep -F '[TREE_COST]' "$d/budget.log"
