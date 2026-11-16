#!/bin/sh
# The rs-prefix block reused the ELF slots. Relink only the adjacent candidate,
# verify the retained baseline hash, and restore the slots even on failure.
set -eu
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/wide-start
test ! -L "$d/replay" && test -x "$d/replay" && test -x "$d/limit"
for arm in original limit; do
 for i in 1 2 3 4; do grep -qF 'reason=verified 120 original demo frames' "$d/delta-adjacent-$arm-$i.log"; done
done
echo "cf0e973c56168647c08d4957b01c7287c43faaac100c6f6ae654f28684db61fa  $d/replay" | sha256sum -c -
saved=$(mktemp -d "$d/.adjacent-confirm.XXXXXX")
mv "$d/replay" "$saved/ref"
restore(){ if [ -f "$saved/ref" ]; then mv -f "$saved/ref" "$d/replay"; fi; rmdir "$saved"; }
trap restore EXIT
python3 "$p/wide-motion.py" --serial --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --delta-adjacent
sha256sum "$d/replay" "$saved/ref"
for arm in limit-1 original-1 original-2 limit-2 limit-3 original-3 original-4 limit-4; do
 case "$arm" in original*) bin="$saved/ref";; *) bin="$d/replay";; esac
 NGB_OPEN_REPLAY="$bin" sh "$p/run-wide.sh" "delta-adjacent-confirm-$arm"
done
for report in page-limit-report work-match work-ledger; do python3 "$p/$report.py" "$d" delta-adjacent-confirm; done
