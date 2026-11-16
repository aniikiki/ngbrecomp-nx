#!/bin/sh
set -eu
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/opening-present-combined
mkdir -p "$d/hdd"
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
trap 'rm -f "$d/host/replay" "$d/whole-base" "$d/whole-retained" "$d/whole-split" "$d/host/unmetered-memory.o" "$d/host/unmetered-trig.o"' EXIT
for arm in base retained split; do
 set -- --target-library-pair
 if [ "$arm" != base ]; then set -- "$@" --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy; fi
 if [ "$arm" = split ]; then set -- "$@" --partition-pgo; fi
 python3 "$p/wide-motion.py" --serial --present-mix --present-combined "$@"
 python3 "$p/seed-replay-elf.py" "$d/host/replay"
 for n in sin cos memcmp memcpy memmove memset; do
  nm --defined-only "$d/host/replay" | grep -q " T __wrap_$n$"
 done
 mv "$d/host/replay" "$d/whole-$arm"
done
for name in base-1 retained-1 split-1 retained-2 split-2 base-2 split-3 base-3 retained-3; do
 "$d/whole-${name%-*}" --start-button game_files "$d/hdd" >"$d/targetlibs-$name.log" 2>&1 || :
 grep -Fq 'reason=verified 120 original demo frames' "$d/targetlibs-$name.log"
done
