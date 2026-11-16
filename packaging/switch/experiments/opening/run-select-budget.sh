#!/bin/sh
set -eu
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/opening-rng-correspondence
h=$d/host
trap 'rm -f "$h/replay"' EXIT
python3 "$p/wide-motion.py" --serial --present-mix --rng-correspondence --target-library-pair --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --partition-pgo --select-budget
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache NGB_REPLAY_FIXED_SEED=1
for i in 1 2; do
"$h/replay" --start-button game_files "$d/hdd" >"$d/select-budget-$i.log" 2>&1 || :
grep -Fq 'verified 120 original demo frames' "$d/select-budget-$i.log"
done
