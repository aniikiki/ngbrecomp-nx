#!/bin/sh
set -eu
case "${1:-first}" in
 first) tag=transform-page-copy; order="split-1 original-1 original-2 split-2";;
 reverse) tag=transform-page-reverse; order="original-1 split-1 split-2 original-2";;
 *) exit 2;;
esac
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/opening-rng-correspondence
mkdir -p "$d/hdd"
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
trap 'rm -f "$d/host/replay" "$d/original" "$d/split"' EXIT
set -- --serial --present-mix --rng-correspondence --target-library-pair --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --partition-pgo
for arm in original split; do
 if [ "$arm" = original ]; then python3 "$p/wide-motion.py" "$@"; else python3 "$p/wide-motion.py" "$@" --transform-page-copy; fi
 mv "$d/host/replay" "$d/$arm"
done
export NGB_REPLAY_FIXED_SEED=1
for name in $order; do
 "$d/${name%-*}" --start-button game_files "$d/hdd" >"$d/$tag-$name.log" 2>&1 || :
 grep -Fq 'verified 120 original demo frames' "$d/$tag-$name.log"
done
grep -Fq "[TRANSFORM_PAGE] used" "$d/$tag-split-1.log"
grep -Fq "[TRANSFORM_PAGE] used" "$d/$tag-split-2.log"
