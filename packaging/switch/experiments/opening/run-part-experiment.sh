#!/bin/sh
# Run inside ngb-switch-host:direct0331, from /work.
set -eu
p=packaging/switch/experiments/opening
case "${1:-}" in
  part-state|part-constants|delta-mask|defer-fixed|fixed-writers) exp=$1 ;;
  *) exit 2 ;;
esac
d=build/switch-runtime/core-perf/opening-$exp
python3 "$p/$exp.py"
runner=$(mktemp)
trap 'rm -f "$runner"' EXIT
sed "s@core-perf/opening-setup@core-perf/opening-$exp@" "$p/run.sh" >"$runner"
if [ "$exp" = part-state ]; then sh "$runner" inputs; exit; fi
NGB_OPEN_CHECK=1 sh "$runner" audit
sh "$runner" ab
NGB_OPEN_REVERSE=1 sh "$runner" ba
python3 "$p/report.py" "$d/ab.log" "$d/ba.log"
