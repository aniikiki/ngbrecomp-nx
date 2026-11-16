#!/bin/sh
set -eu
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/opening-rng-correspondence
mkdir -p "$d/hdd"
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
trap 'rm -f "$d/host/replay" "$d/cached" "$d/copied"' EXIT
for arm in cached copied; do
 set --
 set -- --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --target-library-pair
 set -- "$@" --partition-pgo
 if [ "$arm" = copied ]; then set -- "$@" --copy-index-batch; fi
 python3 "$p/wide-motion.py" --serial --present-mix --rng-correspondence "$@"
 mv "$d/host/replay" "$d/$arm"
done
export NGB_REPLAY_FIXED_SEED=1
for name in copied-1 cached-1 cached-2 copied-2; do
 "$d/${name%-*}" --start-button game_files "$d/hdd" >"$d/indexbatch-one-$name.log" 2>&1 || :
 grep -Fq 'verified 120 original demo frames' "$d/indexbatch-one-$name.log"
done
