#!/bin/sh
set -eu
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/opening-rng-correspondence
mkdir -p "$d/hdd"
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
trap 'rm -f "$d/host/replay" "$d/original" "$d/split"' EXIT
for arm in original split; do
 set -- --target-library-pair
 if [ "$arm" = split ]; then set -- "$@" --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --partition-pgo; fi
 python3 "$p/wide-motion.py" --serial --present-mix --rng-correspondence --paced-cumulative "$@"
 mv "$d/host/replay" "$d/$arm"
done
export NGB_REPLAY_FIXED_SEED=1 NGB_DRAW_CADENCE=1
for name in split-1 original-1 original-2 split-2; do
 "$d/${name%-*}" --start-button game_files "$d/hdd" >"$d/paced-cumulative-$name.log" 2>&1 || :
 grep -Fq 'verified 120 original demo frames' "$d/paced-cumulative-$name.log"
done
