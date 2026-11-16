#!/bin/sh
set -eu
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/opening-draw-correspondence
mkdir -p "$d/hdd"
python3 "$p/wide-motion.py" --serial --draw-correspondence --draw-cadence
trap 'rm -f "$d/host/replay"' EXIT
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
for arm in normal paced; do
 if [ "$arm" = paced ]; then export NGB_DRAW_CADENCE=1; else unset NGB_DRAW_CADENCE; fi
 "$d/host/replay" --start-button game_files "$d/hdd" > "$d/$arm.log" 2>&1 || :
 grep -Fq 'verified 120 original demo frames' "$d/$arm.log"
done
