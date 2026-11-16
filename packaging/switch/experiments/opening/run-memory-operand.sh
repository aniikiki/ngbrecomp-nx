#!/bin/sh
set -eu
p=packaging/switch/experiments/opening
root=build/switch-runtime/core-perf
d=$root/opening-outside-operand
host=$root/opening-present-combined/host
mkdir -p "$d"
trap 'rm -f "$host/replay"' EXIT
python3 "$p/wide-motion.py" --serial --present-mix --present-combined --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --target-library-pair --partition-pgo --frame-pc --xdk-pc-scope --xdk-memory-operand
python3 "$p/seed-replay-elf.py" "$host/replay"
nm -nS --defined-only "$host/replay" | awk '$3 ~ /^[tTwW]$/{print}' > "$d/symbols.txt"
nm -nS --defined-only "$host/replay" | awk 'NF==4 && $3 ~ /^[bBdDrR]$/' > "$d/data-symbols.txt"
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
for i in 1 2 3 4; do
 if [ "$i" = 2 ] || [ "$i" = 4 ]; then export NGB_PC_REPEAT=1; else unset NGB_PC_REPEAT; fi
 "$host/replay" --start-button game_files "$root/opening-present-combined/hdd" >"$d/run-$i.log" 2>&1 || :
 grep -Fq 'reason=verified 120 original demo frames' "$d/run-$i.log"
 grep -q '^\[FRAME_PC_COUNT\]' "$d/run-$i.log"
done
python3 "$p/split-profile-report.py" "$d" "$host/replay" > "$d/profile.txt"
python3 "$p/outside-operand-report.py" "$d" > "$d/summary.txt"
