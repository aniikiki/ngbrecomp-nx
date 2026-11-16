#!/bin/sh
set -eu
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/opening-rng-correspondence
mkdir -p "$d/hdd"
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
trap 'rm -f "$d/host/replay" "$d/original" "$d/split"' EXIT
set -- --serial --present-mix --rng-correspondence --target-library-pair --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --partition-pgo
for arm in original split; do
 if [ "$arm" = original ]; then python3 "$p/wide-motion.py" "$@"; else python3 "$p/wide-motion.py" "$@" --align-hot-entry; fi
 mv "$d/host/replay" "$d/$arm"
 nm -n --defined-only "$d/$arm" | awk 'NR==FNR{want["ngb_reg_"$1]=1;next} $3 in want {print $3,$1}' build/switch-runtime/core-perf/opening-align-hot-entry/entries.txt - >"$d/align-hot-entry-$arm.addr"
done
python3 - "$d" <<'CHECK'
import sys
from pathlib import Path
d=Path(sys.argv[1])
def offsets(arm):
 return {n:int(a,16)%64 for n,a in (l.split() for l in (d/f'align-hot-entry-{arm}.addr').read_text().splitlines())}
a,b=offsets('original'),offsets('split')
assert len(a)==32 and a.keys()==b.keys() and any(a.values()) and not any(b.values())
print('entry offsets changed',sum(bool(x) for x in a.values()),flush=True)
CHECK
export NGB_REPLAY_FIXED_SEED=1
for name in split-1 original-1 original-2 split-2; do
 "$d/${name%-*}" --start-button game_files "$d/hdd" >"$d/align-hot-entry-$name.log" 2>&1 || :
 grep -Fq 'verified 120 original demo frames' "$d/align-hot-entry-$name.log"
done
