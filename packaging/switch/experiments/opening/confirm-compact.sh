#!/bin/sh
# Follow the discovery block with the opposite order using the identical two ELFs.
set -eu
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/wide-start
case "${1:-compact-loops}" in
 compact-loops) previous=compact-loops; tag=compact-confirm;;
 row-ceiling) previous=row-ceiling; tag=row-ceiling-confirm;;
 program-range) previous=program-range; tag=program-range-confirm;;
 push-scratch) previous=push-scratch; tag=push-scratch-confirm;;
 model-copy) previous=model-copy; tag=model-copy-confirm;;
 scope-floor) previous=scope-floor; tag=scope-floor-confirm;;
 light-before) previous=light-before; tag=light-before-confirm;;
 literal-xmm) previous=literal-xmm; tag=literal-xmm-confirm;;
 known-difference) previous=known-difference; tag=known-difference-confirm;;
 paired-copy) previous=paired-copy; tag=paired-copy-confirm;;
 fifo-last-state) previous=fifo-last-state; tag=fifo-last-confirm;;
 cmd-target) previous=cmd-target; tag=cmd-confirm;;
 entry-mask) previous=entry-mask; tag=entry-mask-confirm;;
 reg-base) previous=reg-base; tag=reg-confirm;;
 timer-mask) previous=timer-mask; tag=timer-confirm;;
 *) exit 2;;
esac
test -x "$d/replay" && test -x "$d/limit" && test ! -L "$d/replay"
for arm in original limit; do
 for n in 1 2 3 4; do
   grep -Fq 'reason=verified 120 original demo frames' "$d/$previous-$arm-$n.log"
 done
done
sha256sum "$d/replay" "$d/limit"
for a in limit-1 original-1 original-2 limit-2 limit-3 original-3 original-4 limit-4; do
 case "$a" in limit*) bin=limit;; *) bin=replay;; esac
 NGB_OPEN_REPLAY="$d/$bin" sh "$p/run-wide.sh" "$tag-$a"
done
python3 "$p/page-limit-report.py" "$d" "$tag"
python3 "$p/work-match.py" "$d" "$tag"
python3 "$p/work-ledger.py" "$d" "$tag"
