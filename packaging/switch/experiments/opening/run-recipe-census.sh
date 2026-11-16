#!/bin/sh
set -eu
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/opening-present-combined
cache=$(mktemp -d)
trap 'rm -rf "$cache"; rm -f "$d/host/replay"' EXIT
python3 "$p/wide-motion.py" --serial --present-mix --present-combined --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --target-library-pair --partition-pgo --title-worker-prep --title-pipeline-prep
python3 "$p/seed-replay-elf.py" "$d/host/replay"
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache NGB_D3D_CACHE="$cache" NGB_OPEN_RECIPE_CENSUS=1
log="$d/recipe-extent.log"
"$d/host/replay" --start-button game_files "$d/hdd" >"$log" 2>&1 || :
python3 "$p/recipe-subset.py" "$cache/recipes.bin" "$log" "$d"
