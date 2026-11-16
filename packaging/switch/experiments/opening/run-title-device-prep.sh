#!/bin/sh
set -eu
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/opening-present-combined
prefix=overlayprep
option=--title-device-prep
if [ "${1:-}" = worker ]; then prefix=workerprep; option=--title-worker-prep; fi
mkdir -p "$d/hdd"
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
trap 'rm -f "$d/host/replay" "$d/ordinary" "$d/prepared"' EXIT
for arm in ordinary prepared; do
 set --
 set -- --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --target-library-pair
 set -- "$@" --partition-pgo
 if [ "$arm" = prepared ]; then set -- "$@" "$option"; fi
 python3 "$p/wide-motion.py" --serial --present-mix --present-combined "$@"
 python3 "$p/seed-replay-elf.py" "$d/host/replay"
 mv "$d/host/replay" "$d/$arm"
done
for name in ordinary-1 prepared-1 prepared-2 ordinary-2; do
 "$d/${name%-*}" --start-button game_files "$d/hdd" >"$d/$prefix-$name.log" 2>&1 || :
 if [ "${name%-*}" = prepared ]; then
  grep -Fq '[IDLE_DEVICE] ready=1' "$d/$prefix-$name.log"
  grep -Fq '[IDLE_DEVICE] adopted at scene start' "$d/$prefix-$name.log"
 fi
 grep -Fq 'verified 120 original demo frames' "$d/$prefix-$name.log"
done
