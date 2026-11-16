#!/bin/sh
set -eu
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/opening-present-combined
trap 'rm -f "$d/host/replay" "$d/joint-base" "$d/joint-next"' EXIT
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin NGB_D3D_SEED=/work/build/switch-runtime/direct/cache/recipes.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
prefix=joint
extra=
if [ "${1:-}" = buffered ]; then prefix=jointbuf;extra=--buffer-frame-log; fi
for mode in base next; do
 set -- $extra --serial --present-mix --present-combined --target-library-pair
 if [ "$mode" = next ]; then
   set -- "$@" --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --partition-pgo --title-worker-prep --title-pipeline-prep --pixel-write-plan
 fi
 python3 "$p/wide-motion.py" "$@"
 python3 "$p/seed-replay-elf.py" "$d/host/replay"
 mv "$d/host/replay" "$d/joint-$mode"
done
for arm in base-1 next-1 next-2 base-2; do
 unset NGB_OPEN_WARM_PIPELINES
 case "$arm" in next-*) export NGB_OPEN_WARM_PIPELINES=1;; esac
 log="$d/$prefix-$arm.log"
 "$d/joint-${arm%-*}" --start-button game_files "$d/hdd" >"$log" 2>&1 || :
 grep -Fq 'verified 120 original demo frames' "$log"
 case "$arm" in next-*) grep -Fq '[IDLE_DEVICE] adopted at scene start' "$log"; grep -Eq '[1-9][0-9]* pipelines made ahead' "$log";; esac
done
