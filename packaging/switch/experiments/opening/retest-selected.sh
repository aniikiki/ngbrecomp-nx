#!/bin/sh
# A single replay writer. Must run after standalone builds have exited.
set -eu
p=packaging/switch/experiments/opening
flags=$(python3 "$p/eligible-combination.py")
if test -n "$flags"; then
  # flags come only from the static allowlist in the script above.
  sh "$p/run-page-limit.sh" $flags
  python3 "$p/target-gap.py" combined
else
  echo 'No compatible, independently positive pair; no composite time claimed.'
fi
