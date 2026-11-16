#!/bin/sh
set -eu
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/opening-present-combined
mkdir -p "$d/hdd"
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
trap 'rm -f "$d/host/replay" "$d/base-full" "$d/ten-full"' EXIT
for arm in base-full ten-full; do
 set -- --target-library-pair
 if [ "$arm" = ten-full ]; then set -- "$@" --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --partition-pgo --extra-partition; fi
 python3 "$p/wide-motion.py" --serial --present-mix --present-combined "$@"
 python3 "$p/seed-replay-elf.py" "$d/host/replay"
 mv "$d/host/replay" "$d/$arm"
done
for name in ten-full-1 base-full-1 base-full-2 ten-full-2; do
 "$d/${name%-*}" --start-button game_files "$d/hdd" >"$d/extrapg-all-$name.log" 2>&1 || :
 grep -Fq 'verified 120 original demo frames' "$d/extrapg-all-$name.log"
done
