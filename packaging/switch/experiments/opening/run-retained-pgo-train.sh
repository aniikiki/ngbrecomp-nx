#!/bin/sh
set -eu
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/opening-present-combined
pg=build/switch-runtime/core-perf/opening-retained-pgo
variant=
if [ "${1:-}" = local ]; then pg="$pg-local"; variant=--retained-pgo-local; fi
mkdir -p "$d/hdd"
trap 'rm -f "$d/host/replay"' EXIT
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
python3 "$p/wide-motion.py" --serial --present-mix --present-combined --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --retained-pgo-train $variant
"$d/host/replay" --start-button game_files "$d/hdd" >"$pg/training.log" 2>&1 || :
grep -Fq 'reason=verified 120 original demo frames' "$pg/training.log"
grep -Fq '[TRAIN] wrote 5 profiles' "$pg/training.log"
