#!/bin/sh
set -eu
d=build/switch-runtime/core-perf/opening-present-combined
p=packaging/switch/experiments/opening
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
trap 'rm -f "$d/host/replay"' EXIT
python3 "$p/wide-motion.py" --serial --present-mix --present-combined --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --target-trig
python3 "$p/seed-replay-elf.py" "$d/host/replay"
for i in 1 2; do
 log="build/switch-runtime/core-perf/opening-target-trig/run-$i.log"
 "$d/host/replay" --start-button game_files "$d/hdd" >"$log" 2>&1 || :
 grep -Fq 'reason=verified 120 original demo frames' "$log"
 test "$(grep -c '^\[TARGET_TRIG\]' "$log")" = 4
done
