#!/bin/sh
set -eu
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/opening-present-combined
mkdir -p "$d/hdd"
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
trap 'rm -f "$d/host/replay" "$d/base" "$d/retained" "$d/combined"' EXIT
for arm in base retained combined; do
 set --
 if [ "$arm" != base ]; then set -- --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy; fi
 if [ "$arm" = combined ]; then set -- "$@" --cmd-service-span --material-compare-chain; fi
 python3 "$p/wide-motion.py" --serial --present-mix --present-combined "$@"
 mv "$d/host/replay" "$d/$arm"
done
for name in base-1 retained-1 combined-1 retained-2 combined-2 base-2 combined-3 base-3 retained-3; do
 "$d/${name%-*}" --start-button game_files "$d/hdd" >"$d/$name.log" 2>&1 || :
 grep -Fq 'verified 120 original demo frames' "$d/$name.log"
done
