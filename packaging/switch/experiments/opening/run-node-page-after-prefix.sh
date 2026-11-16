#!/bin/sh
# Host-side: serialize the pending correctness census and timing, sharing one worktree.
set -eu
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/opening-node-prefix
if docker ps --format '{{.Names}}' | grep -qx ngb-node-prefix-run; then
 docker wait ngb-node-prefix-run >/dev/null
fi
grep -Fq 'reason=verified 120 original demo frames' "$d/budget.log"
test "$(grep -cF '[NODE_PREFIX]' "$d/budget.log")" = 6
docker run --rm --name ngb-node-page-build -v "$PWD:/work" -w /work ngb-switch-nxvk:dev python3 "$p/node-page-run.py"
docker run --rm --name ngb-node-page-replay -v "$PWD:/work" -w /work ngb-switch-host:direct0331 sh "$p/run-page-limit.sh" --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --node-page-run
