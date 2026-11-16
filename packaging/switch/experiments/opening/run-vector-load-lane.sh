#!/bin/sh
set -eu
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/opening-present-combined
mkdir -p "$d/hdd"
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
trap 'rm -f "$d/host/replay" "$d/retained" "$d/vector-load-lane"' EXIT
for arm in retained vector-load-lane; do
 set --
 set -- --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy
 if [ "$arm" = vector-load-lane ]; then set -- "$@" --vector-load-lane; fi
 python3 "$p/wide-motion.py" --serial --present-mix --present-combined "$@"
 python3 "$p/seed-replay-elf.py" "$d/host/replay"
 mv "$d/host/replay" "$d/$arm"
done
for name in retained-1 vector-load-lane-1 vector-load-lane-2 retained-2; do
 "$d/${name%-*}" --start-button game_files "$d/hdd" >"$d/lane-$name.log" 2>&1 || :
 grep -Fq 'verified 120 original demo frames' "$d/lane-$name.log"
done
