#!/bin/sh
set -eu
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/opening-present-combined
mkdir -p "$d/hdd"
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
trap 'rm -f "$d/host/replay" "$d/retained" "$d/fixed-mask-packet"' EXIT
for arm in retained fixed-mask-packet; do
 set --
 set -- --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy
 if [ "$arm" = fixed-mask-packet ]; then set -- "$@" --fixed-mask-packet; fi
 python3 "$p/wide-motion.py" --serial --present-mix --present-combined "$@"
 python3 "$p/seed-replay-elf.py" "$d/host/replay"
 mv "$d/host/replay" "$d/$arm"
done
for name in retained-1 fixed-mask-packet-1 fixed-mask-packet-2 retained-2; do
 "$d/${name%-*}" --start-button game_files "$d/hdd" >"$d/maskpkt-$name.log" 2>&1 || :
 grep -Fq 'verified 120 original demo frames' "$d/maskpkt-$name.log"
done
