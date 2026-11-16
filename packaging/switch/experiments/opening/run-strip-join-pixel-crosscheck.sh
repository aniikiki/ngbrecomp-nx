#!/bin/sh
set -eu
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/opening-present-combined
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
trap 'rm -f "$d/host/replay"' EXIT
python3 "$p/wide-motion.py" --serial --present-mix --present-combined --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --shader-bank --recipe-pixels --strip-snapshot-join
python3 "$p/seed-replay-elf.py" "$d/host/replay"
for name in control-1 joined-1 joined-2 control-2; do
 case "$name" in control-*) export NGB_STRIP_JOIN_CONTROL=1;; *) unset NGB_STRIP_JOIN_CONTROL;; esac
 "$d/host/replay" --start-button game_files "$d/hdd" >"$d/strip-cross-$name.log" 2>&1 || :
 grep -Fq 'verified 120 original demo frames' "$d/strip-cross-$name.log"
done
