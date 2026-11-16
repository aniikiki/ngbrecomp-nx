#!/bin/sh
set -eu
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/opening-present-combined
mkdir -p "$d/hdd"
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
trap 'rm -f "$d/host/replay" "$d/cached" "$d/copied"' EXIT
for arm in cached copied; do
 set --
 set -- --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --target-library-pair
 set -- "$@" --partition-pgo
 if [ "$arm" = copied ]; then set -- "$@" --copy-index-batch; fi
 python3 "$p/wide-motion.py" --serial --present-mix --present-combined "$@"
 python3 "$p/seed-replay-elf.py" "$d/host/replay"
 mv "$d/host/replay" "$d/$arm"
done
for name in cached-1 copied-1 copied-2 cached-2; do
 "$d/${name%-*}" --start-button game_files "$d/hdd" >"$d/indexbatch-$name.log" 2>&1 || :
 grep -Fq 'verified 120 original demo frames' "$d/indexbatch-$name.log"
done
