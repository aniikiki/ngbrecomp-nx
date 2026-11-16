#!/bin/sh
set -eu
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/opening-present-combined
trap 'rm -f "$d/host/replay"' EXIT
opts=
prefix=recipeprep
arms="warm-1 base-1 base-2 warm-2"
if [ "${1:-}" = clip-record ]; then opts=--clip-record-cost;prefix=cliprecord;arms="base-1"; fi
if [ "${1:-}" = bias-neighbors ]; then opts="--draw-neighbors --geom-neighbors --bias-neighbors";prefix=biasneighbors;arms="base-1"; fi
if [ "${1:-}" = geom-neighbors ]; then opts="--draw-neighbors --geom-neighbors";prefix=geomneighbors;arms="base-1"; fi
if [ "${1:-}" = neighbors ]; then opts=--draw-neighbors;prefix=neighbors;arms="base-1"; fi
if [ "${1:-}" = cold-cost ]; then opts=--cold-cost;prefix=coldcost;arms="base-1"; fi
if [ "${1:-}" = retry ]; then opts=--recipe-retry;prefix=reciperetry;arms="warm-1"; fi
if [ "${1:-}" = sources ]; then opts=--recipe-sources;prefix=recipesources;arms=warm-small-1; fi
if [ "${1:-}" = first30 ]; then
 prefix=recipefirst30;arms=warm-front-1
 test -s "$d/opening-30.recipes"
 export NGB_OPEN_COUNT_CREATES=1
fi
if [ "${1:-}" = subset ]; then
 prefix=recipesubset;arms="warm-small-1 warm-full-1 warm-full-2 warm-small-2"
 test -s "$d/opening-120.recipes"
 export NGB_OPEN_COUNT_CREATES=1
fi
if [ "${1:-}" = pixels ]; then opts=--recipe-pixels;prefix=recipepixels;arms="base-1 warm-1"; fi
if [ "${1:-}" = diff ]; then
 opts=--recipe-pixels;prefix=recipediff;arms="ref-0 base-1 warm-1 warm-2"
 NGB_OPEN_PIXEL_DIFF=$(mktemp -d); export NGB_OPEN_PIXEL_DIFF
 trap 'rm -rf "$NGB_OPEN_PIXEL_DIFF"; rm -f "$d/host/replay"' EXIT
fi
python3 "$p/wide-motion.py" $opts --serial --present-mix --present-combined --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --target-library-pair --partition-pgo --title-worker-prep --title-pipeline-prep
python3 "$p/seed-replay-elf.py" "$d/host/replay"
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin NGB_D3D_SEED=/work/build/switch-runtime/direct/cache/recipes.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
for arm in $arms; do
 unset NGB_OPEN_WARM_PIPELINES NGB_OPEN_PIXEL_REFERENCE
 if [ "$arm" = ref-0 ]; then export NGB_OPEN_PIXEL_REFERENCE=1; fi
 case "$arm" in warm-*) export NGB_OPEN_WARM_PIPELINES=1;; esac
 case "$arm" in
  warm-front-*) export NGB_D3D_SEED="/work/$d/opening-30.recipes";;
  warm-small-*) export NGB_D3D_SEED="/work/$d/opening-120.recipes";;
  warm-full-*) export NGB_D3D_SEED=/work/build/switch-runtime/direct/cache/recipes.bin;;
 esac
 log="$d/$prefix-$arm.log"
 "$d/host/replay" --start-button game_files "$d/hdd" >"$log" 2>&1 || :
 grep -Fq '[IDLE_DEVICE] adopted at scene start' "$log"
 grep -Fq 'verified 120 original demo frames' "$log"
 if [ "${1:-}" = retry ]; then
   grep -Fq '[RECIPE_RETRY] Module recovered' "$log"
   grep -Fq '[RECIPE_RETRY] Pipeline recovered' "$log"
 fi
 case "$arm" in warm-*) grep -Eq '[1-9][0-9]* pipelines made ahead' "$log";; esac
done
