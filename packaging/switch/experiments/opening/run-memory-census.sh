#!/bin/sh
# Non-timing instrumented run in a private directory; never overwrite ABBA pairs.
set -eu
p=packaging/switch/experiments/opening
mode=${1:-memory-census}
case "$mode" in tree-census) marker=TREE_CENSUS;; gate-census) marker=GATE_CENSUS;; pointer-route) marker=PTR_ROUTE;; cmd-budget) marker=CMD_BUDGET;; cmd-pass) marker=CMD_PASS;; box-budget) marker=BOX_BUDGET;; box-scan) marker=BOX_SCAN;; box-reuse) marker=BOX_REUSE;; page-shape) marker=PAGE_SHAPE;; contact-repeat) marker=CONTACT_REPEAT;; contact-blocks) marker=CONTACT_BLOCKS;; frame-pc) marker=FRAME_PC_COUNT;; poll-sample) marker=POLL_SAMPLE;; first-init) marker=FIRST_INIT;; actor-time) marker=ACTOR_TIME;; actor-kinds) marker=ACTOR_KINDS;; product-reuse) marker=PRODUCT_REUSE;; actor-phase) marker=ACTOR_PHASE;; cb-cost|task-cb|task-edges) marker=CB_COST;; tree-update) marker=TREE_UPDATE;; model-nodes) marker=MODEL_NODES;; irq-cost) marker=IRQ_COST;; memory-census) marker=MEM_CENSUS;; span-audit) marker=SPAN_COUNT;; *) exit 2;; esac
d=build/switch-runtime/core-perf/opening-$mode
mkdir -p "$d/hdd"
if [ "$mode" = gate-census ]; then
 python3 "$p/wide-motion.py" --serial --gate-census --gate-high --full-page --command-record --batch-bytes --page-hot-o3
elif [ "$mode" = pointer-route ] || [ "$mode" = tree-census ]; then
 python3 "$p/wide-motion.py" --serial "--$mode" --full-page --command-record --batch-bytes --page-hot-o3
else
 python3 "$p/wide-motion.py" --serial "--$mode"
fi
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json
export NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
"$d/host/replay" --start-button game_files "$d/hdd" > "$d/distribution.log" 2>&1 || :
grep -qF '[RESULT] status=1 reason=verified 120 original demo frames' "$d/distribution.log"
grep -F "[$marker]" "$d/distribution.log"
if [ "$mode" = frame-pc ]; then
 nm -nS --defined-only "$d/host/replay" | awk '$3 ~ /^[tTwW]$/ {print}' > "$d/text-symbols.txt"
fi
rm "$d/host/replay"
