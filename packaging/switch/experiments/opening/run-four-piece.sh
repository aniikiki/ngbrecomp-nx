#!/bin/sh
set -eu
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/opening-present-combined
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
trap 'rm -f "$d/host/replay"' EXIT
python3 "$p/wide-motion.py" --serial --present-mix --present-combined --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --pixel-write-plan --partition-pgo --target-library-pair --four-piece
python3 "$p/seed-replay-elf.py" "$d/host/replay"
for name in verify control-1 planned-1 planned-2 control-2; do
 unset NGB_FOUR_CONTROL NGB_FOUR_VERIFY
 case "$name" in control-*) export NGB_FOUR_CONTROL=1;; verify) export NGB_FOUR_VERIFY=1;; esac
 "$d/host/replay" --start-button game_files "$d/hdd" >"$d/four-piece-$name.log" 2>&1 || :
 grep -Fq 'verified 120 original demo frames' "$d/four-piece-$name.log"
 if [ "$name" = verify ]; then grep -qF "[FOUR_PIECE]" "$d/four-piece-$name.log"; fi
done
