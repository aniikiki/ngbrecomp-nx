#!/bin/sh
set -eu
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/opening-rng-correspondence
mkdir -p "$d/hdd"
trap 'rm -f "$d/seed-base" "$d/seed-retained" "$d/host/replay"' EXIT
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache NGB_REPLAY_FIXED_SEED=1
for arm in base retained; do
 set -- --full-page
 if [ "$arm" = retained ]; then set -- "$@" --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy; fi
 python3 "$p/wide-motion.py" --serial --present-mix --rng-correspondence "$@"
 mv "$d/host/replay" "$d/seed-$arm"
done
for run in base-1 retained-1 retained-2 base-2; do
 "$d/seed-${run%-*}" --start-button game_files "$d/hdd" >"$d/seed-$run.log" 2>&1 || :
 grep -Fq 'reason=verified 120 original demo frames' "$d/seed-$run.log"
done
