#!/bin/sh
set -eu
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/opening-rng-correspondence
mkdir -p "$d/hdd"
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
trap 'rm -f "$d/host/replay" "$d/psr-control" "$d/psr-trial"' EXIT
for arm in psr-control psr-trial; do
 set -- --target-library-pair --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --partition-pgo --pixel-write-plan
 if [ "$arm" = psr-trial ]; then set -- "$@" --ps-range-epoch; fi
 python3 "$p/wide-motion.py" --serial --present-mix --rng-correspondence "$@"
 mv "$d/host/replay" "$d/$arm"
done
export NGB_REPLAY_FIXED_SEED=1
for name in psr-trial-1 psr-control-1 psr-control-2 psr-trial-2; do
 "$d/${name%-*}" --start-button game_files "$d/hdd" >"$d/holdout-$name.log" 2>&1 || :
 grep -Fq 'verified 120 original demo frames' "$d/holdout-$name.log"
done
