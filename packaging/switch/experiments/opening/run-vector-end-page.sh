#!/bin/sh
set -eu
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/opening-present-combined
mkdir -p "$d/hdd"
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
trap 'rm -f "$d/host/replay" "$d/retained" "$d/vector-end-page"' EXIT
for unit in 0002 0010 0016 0028 0029; do
 obj=build/switch-runtime/core-perf/opening-vector-end-page/recomp_$unit.c
 grep -Fq '/opening-vector-end-page/recomp_types.h' "$obj.d"
 test -s "$obj.o"
done
for arm in retained vector-end-page; do
 set --
 set -- --target-library-pair --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy
 if [ "$arm" = vector-end-page ]; then set -- "$@" --vector-end-page; fi
 python3 "$p/wide-motion.py" --serial --present-mix --present-combined "$@"
 python3 "$p/seed-replay-elf.py" "$d/host/replay"
 mv "$d/host/replay" "$d/$arm"
done
for name in retained-1 vector-end-page-1 vector-end-page-2 retained-2; do
 "$d/${name%-*}" --start-button game_files "$d/hdd" >"$d/endpage-$name.log" 2>&1 || :
 grep -Fq 'verified 120 original demo frames' "$d/endpage-$name.log"
done
