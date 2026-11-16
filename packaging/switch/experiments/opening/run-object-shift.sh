#!/bin/sh
set -eu
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/opening-present-combined
python3 "$p/object-shift.py"
python3 "$p/wide-motion.py" --serial --present-mix --present-combined --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --object-shift
python3 "$p/seed-replay-elf.py" "$d/host/replay"
trap 'rm -f "$d/host/replay"' EXIT
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
for arm in verify control-1 planned-1 planned-2 control-2; do
 unset NGB_SHIFT_ON NGB_SHIFT_CHECK
 case "$arm" in verify) export NGB_SHIFT_CHECK=1;; planned-*) export NGB_SHIFT_ON=1;; esac
 log="$d/object-shift-$arm.log"
 "$d/host/replay" --start-button game_files "$d/hdd" >"$log" 2>&1 || :
 grep -Fq 'verified 120 original demo frames' "$log"
 if [ "$arm" = verify ]; then grep -Fq '[SHIFT_CHECK]' "$log"; fi
done
