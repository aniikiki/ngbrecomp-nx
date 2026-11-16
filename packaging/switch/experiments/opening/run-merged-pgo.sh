#!/bin/sh
set -eu
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/opening-present-combined
mkdir -p "$d/hdd"
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
trap 'rm -f "$d/host/replay" "$d/control" "$d/guided"' EXIT
for arm in control guided; do
 set --
 set --
 if [ "$arm" = guided ]; then set -- --merged-pgo; fi
 python3 "$p/wide-motion.py" --serial --present-mix --present-combined "$@"
 python3 "$p/seed-replay-elf.py" "$d/host/replay"
 mv "$d/host/replay" "$d/$arm"
done

for name in control-1 guided-1 guided-2 control-2; do
 "$d/${name%-*}" --start-button game_files "$d/hdd" >"$d/mergedpgo-$name.log" 2>&1 || :
 grep -Fq 'verified 120 original demo frames' "$d/mergedpgo-$name.log"
done
