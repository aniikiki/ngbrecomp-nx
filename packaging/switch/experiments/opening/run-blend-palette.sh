#!/bin/sh
set -eu
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/opening-present-combined
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
trap 'rm -f "$d/host/replay"' EXIT
python3 "$p/wide-motion.py" --serial --present-mix --present-combined --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --partition-pgo --target-library-pair --blend-palette --buffer-frame-log
python3 "$p/seed-replay-elf.py" "$d/host/replay"
for name in control-1 planned-1 planned-2 control-2; do
 unset NGB_PALETTE_CONTROL
 case "$name" in control-*) export NGB_PALETTE_CONTROL=1;; esac
 "$d/host/replay" --start-button game_files "$d/hdd" >"$d/blend-palette-$name.log" 2>&1 || :
 grep -Fq 'verified 120 original demo frames' "$d/blend-palette-$name.log"
done
