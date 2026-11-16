#!/bin/sh
set -eu
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/opening-present-combined
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"; rm -f "$d/host/replay"' EXIT
opts=--recipe-sources
arms="fill check"
if [ "${1:-}" = compare ]; then
 test -s "$d/opening-complete.spirv"
 opts=--buffer-frame-log
 arms="old-1 complete-1 complete-2 old-2"
fi
python3 "$p/wide-motion.py" $opts --serial --present-mix --present-combined --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --target-library-pair --partition-pgo --title-worker-prep --title-pipeline-prep
python3 "$p/seed-replay-elf.py" "$d/host/replay"
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache NGB_D3D_SEED="/work/$d/opening-120.recipes" NGB_OPEN_WARM_PIPELINES=1
export NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin
for arm in $arms; do
 case "$arm" in
  old-*) export NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin;;
  complete-*) export NGB_DIRECT_SPIRV="/work/$d/opening-complete.spirv";;
 esac
 mkdir "$scratch/$arm"
 export NGB_D3D_CACHE="$scratch/$arm"
 log="$d/openingspirv-$arm.log"
 "$d/host/replay" --start-button game_files "$d/hdd" >"$log" 2>&1 || :
 grep -Fq 'reason=verified 120 original demo frames' "$log"
 grep -Fq '118 shaders and 167 pipelines made ahead' "$log"
 if [ "$arm" = fill ]; then
  python3 "$p/complete-opening-spirv.py" "$NGB_DIRECT_SPIRV" "$NGB_D3D_CACHE/spirv.bin" "$log" "$d/opening-complete.spirv"
  export NGB_DIRECT_SPIRV="/work/$d/opening-complete.spirv"
 elif [ "${arm#old-}" != "$arm" ]; then
  grep -Fq 'loaded 93 packaged shaders' "$log"
  test "$(wc -c < "$NGB_D3D_CACHE/spirv.bin")" -gt 8
 else
  grep -Fq 'loaded 98 packaged shaders' "$log"
  test "$(wc -c < "$NGB_D3D_CACHE/spirv.bin")" -eq 8
 fi
done
