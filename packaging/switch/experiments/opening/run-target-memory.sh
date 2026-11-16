#!/bin/sh
set -eu
d=build/switch-runtime/core-perf/opening-present-combined
p=packaging/switch/experiments/opening
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
trap 'rm -f "$d/host/replay"' EXIT
python3 "$p/wide-motion.py" --serial --present-mix --present-combined --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --target-memory
python3 "$p/seed-replay-elf.py" "$d/host/replay"
nm -n "$d/host/replay" | awk '$2 ~ /^[TtWw]$/{print $1,$3}' >build/switch-runtime/core-perf/opening-target-memory/text.txt
for i in 1 2; do
 log="build/switch-runtime/core-perf/opening-target-memory/run-$i.log"
 "$d/host/replay" --start-button game_files "$d/hdd" >"$log" 2>&1 || :
 grep -Fq 'reason=verified 120 original demo frames' "$log"
 grep -q '^\[TARGET_MEMORY\] 120 ' "$log"
done
