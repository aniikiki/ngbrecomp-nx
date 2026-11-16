#!/bin/sh
# Repeat the affected fourth pair without overwriting any original evidence.
set -eu
d=build/switch-runtime/core-perf/wide-start
p=packaging/switch/experiments/opening
for item in full-page original original full-page; do
 case "$item" in
  original) python3 "$p/wide-motion.py" --serial;;
  full-page) python3 "$p/wide-motion.py" --serial --full-page;;
 esac
 case "$item" in
  original) i=${oruns:-0};oruns=$((i+1));i=$oruns;;
  full-page) i=${pruns:-0};pruns=$((i+1));i=$pruns;;
 esac
 sh "$p/run-wide.sh" "full-page-retest-$item-$i"
done
python3 "$p/wide-motion.py" --serial
