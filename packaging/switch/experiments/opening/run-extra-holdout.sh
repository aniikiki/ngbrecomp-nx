#!/bin/sh
set -eu
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/opening-rng-correspondence
mkdir -p "$d/hdd"
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
trap 'rm -f "$d/host/replay" "$d/five" "$d/ten"' EXIT
for arm in five ten; do
 set --
 set -- --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --target-library-pair
 if [ "$arm" = ten ]; then set -- "$@" --partition-pgo --extra-partition; else set -- "$@" --partition-pgo; fi
 python3 "$p/wide-motion.py" --serial --present-mix --rng-correspondence "$@"
 mv "$d/host/replay" "$d/$arm"
done
export NGB_REPLAY_FIXED_SEED=1
for name in ten-1 five-1 five-2 ten-2; do
 "$d/${name%-*}" --start-button game_files "$d/hdd" >"$d/extrapg-one-$name.log" 2>&1 || :
 grep -Fq 'verified 120 original demo frames' "$d/extrapg-one-$name.log"
done
