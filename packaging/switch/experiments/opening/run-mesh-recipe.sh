#!/bin/sh
set -eu
d=build/switch-runtime/core-perf/opening-mesh-recipe-census
trap 'rm -f "$d/replay"' EXIT
python3 packaging/switch/experiments/opening/mesh-recipe-census.py
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
log="$d/${NGB_RECIPE_RANK:+rank-}${NGB_RECIPE_CLOCK:+clock-}${NGB_RECIPE_SETTERS:+setters-}${NGB_RECIPE_FIELDS:+fields-}budget.log"
"$d/replay" --start-button game_files build/switch-runtime/core-perf/opening-present-combined/hdd >"$log" 2>&1 || :
grep -q 'verified 120 original demo frames' "$log"
