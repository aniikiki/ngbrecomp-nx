#!/bin/sh
set -eu
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/opening-present-combined
trap 'rm -f "$d/host/replay" "$d/ps-range-control" "$d/ps-range-planned"' EXIT
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
for name in planned control; do
 set --; if [ "$name" = planned ]; then set -- --ps-range-epoch; fi
 python3 "$p/wide-motion.py" --serial --present-mix --present-combined --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --pixel-write-plan --partition-pgo --target-library-pair "$@"
 python3 "$p/seed-replay-elf.py" "$d/host/replay"
 mv "$d/host/replay" "$d/ps-range-$name"
 if [ "$name" = planned ]; then
   NGB_PS_RANGE_VERIFY=1 "$d/ps-range-planned" --start-button game_files "$d/hdd" >"$d/ps-range-verify.log" 2>&1 || :
   grep -qF 'verified 120 original demo frames' "$d/ps-range-verify.log"
   for i in 0 2 3 5; do grep -qF "[PS_RANGE_CHECK] $i " "$d/ps-range-verify.log"; done
 fi
done
for arm in control-1 planned-1 planned-2 control-2; do
 "$d/ps-range-${arm%-*}" --start-button game_files "$d/hdd" >"$d/ps-range-$arm.log" 2>&1 || :
 grep -qF 'verified 120 original demo frames' "$d/ps-range-$arm.log"
done
