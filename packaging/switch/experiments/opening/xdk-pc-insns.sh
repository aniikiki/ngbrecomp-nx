#!/bin/sh
set -eu
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/opening-xdk-pc-scope
exe=build/switch-runtime/core-perf/opening-present-combined/host/replay
trap 'rm -f "$exe"' EXIT
python3 "$p/wide-motion.py" --serial --present-mix --present-combined --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --target-library-pair --partition-pgo --frame-pc --xdk-pc-scope
python3 "$p/seed-replay-elf.py" "$exe"
nm -nS --defined-only "$exe" | awk '$3 ~ /^[tTwW]$/{print}' | cmp - "$d/symbols.txt"
python3 "$p/split-profile-report.py" "$d" "$exe" >"$d/profile.txt"
python3 "$p/outside-insns.py" >"$d/outside-insns.txt"
