#!/bin/sh
# In the Linux/arm64 host image, from /work. Use a fresh emulated HDD for each arm.
set -eu
python3 packaging/switch/texture-preload/replay.py
d=build/switch-runtime/core-perf/texture-preload-replay
export LP_NUM_THREADS=4 NGB_REPLAY_FIXED_SEED=1 NGB_DIRECT_SPIRV=/work/build/switch-runtime/core-perf/opening-present-combined/opening-complete.spirv VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json
export NGB_D3D_SEED=/work/build/switch-runtime/core-perf/opening-present-combined/opening-120.recipes
for mode in wide; do
 for arm in off on; do
  if [ "$arm" = off ]; then export NGB_DISABLE_TEXTURE_PRELOAD=1; else unset NGB_DISABLE_TEXTURE_PRELOAD; fi
  if [ "$mode" = wide ]; then export NGB_TEST_IDLE_SCENE=benchmark;unset NGB_TEST_STORY;else unset NGB_TEST_IDLE_SCENE;export NGB_TEST_STORY=1;fi
  scratch=$(mktemp -d);export XDG_CACHE_HOME="$scratch/cache"
  "$d/replay" --start-button game_files "$scratch/hdd" > "$d/$mode-$arm.log" 2>&1 || grep -q 'reason=verified 120 original demo frames' "$d/$mode-$arm.log"
  grep -E 'reason=verified (120 original demo frames|first chapter player control)' "$d/$mode-$arm.log"
 done
done
