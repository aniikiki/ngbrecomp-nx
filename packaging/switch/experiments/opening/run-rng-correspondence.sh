#!/bin/sh
set -eu
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/opening-rng-correspondence
mkdir -p "$d/hdd"
trap 'rm -f "$d/host/replay"' EXIT
python3 "$p/wide-motion.py" --serial --present-mix --rng-correspondence --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
for run in natural-1 fixed-1 fixed-2 natural-2; do
 case "$run" in fixed*) export NGB_REPLAY_FIXED_SEED=1;; *) unset NGB_REPLAY_FIXED_SEED;; esac
 "$d/host/replay" --start-button game_files "$d/hdd" > "$d/$run.log" 2>&1 || :
 grep -Fq 'reason=verified 120 original demo frames' "$d/$run.log"
 if [ "$run" = natural-1 ]; then
  # No call to srand anywhere by frame 120: this intervention cannot affect the stream.
  if ! awk '/^\[RNG_PRESENT\]/&&$4>0{changed=1}END{exit !changed}' "$d/$run.log"; then break; fi
 fi
done
