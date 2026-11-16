#!/bin/sh
# Cross-build first with page-limit.py, then run in the ARM host image, serially.
set -eu
# Experiments may register a new tag while these eight long replays run.
# Execute an immutable snapshot so the shell cannot read two file versions.
if [ "${NGB_RUNNER_SNAPSHOT:-}" != 1 ]; then
 snap=$(mktemp)
 trap 'rm -f "$snap"' EXIT
 cp "$0" "$snap"
 NGB_RUNNER_SNAPSHOT=1 sh "$snap" "$@"
 exit 0
fi
p=packaging/switch/experiments/opening
d=build/switch-runtime/core-perf/wide-start
if [ "$#" -eq 0 ]; then set -- --page-limit; fi
variant=$1
tag=${variant#--}
if [ "$#" -gt 1 ]; then tag=combined; fi
if [ "$*" = "--full-page --command-record" ]; then tag=page-record; fi
if [ "$*" = "--full-page --command-record --batch-bytes" ]; then tag=batch-bytes; fi
if [ "$*" = "--full-page --command-record --batch-bytes --batch-headers" ]; then tag=batch-headers; fi
if [ "$*" = "--full-page --command-record --batch-bytes --batch-128" ]; then tag=batch-128; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3" ]; then tag=page-hot-o3; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --page-next-o3" ]; then tag=page-next-o3; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --header-span" ]; then tag=header-span; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --native-draw-o3" ]; then tag=native-draw-o3; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --index-equal" ]; then tag=index-equal; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --state-witness" ]; then tag=state-witness; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --fifo-lookahead" ]; then tag=fifo-lookahead; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --gate-pointer" ]; then tag=gate-pointer; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --gate-high" ]; then tag=gate-high; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --gate-mapped" ]; then tag=gate-mapped; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --history-cost" ]; then tag=history-cost; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --pc-density" ]; then tag=pc-density; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --tree-level" ]; then tag=tree-level; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --tree-null" ]; then tag=tree-null; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --light-clear" ]; then tag=light-clear; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs" ]; then tag=after-regs; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --draw-lto" ]; then tag=draw-lto; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --simple-literal" ]; then tag=simple-literal; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --constant-groups" ]; then tag=constant-groups; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --loop-ira" ]; then tag=loop-ira; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops" ]; then tag=compact-loops; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --fifo-method-table" ]; then tag=fifo-method-table; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --tree-tickets" ]; then tag=tree-tickets; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --material-inline" ]; then tag=material-inline; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --light-zero" ]; then tag=light-zero; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --light-record" ]; then tag=light-record; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --entry-literal" ]; then tag=entry-literal; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --poll-inline" ]; then tag=poll-inline; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --cmd-target" ]; then tag=cmd-target; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --node-walk" ]; then tag=node-walk; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --node-page-run" ]; then tag=node-page-run; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --checkpoint-loads" ]; then tag=checkpoint-loads; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --entry-mask" ]; then tag=entry-mask; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --vblank-window" ]; then tag=vblank-window; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --batch-handoff" ]; then tag=batch-handoff; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --header-fold" ]; then tag=header-fold; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --stream-layout" ]; then tag=stream-layout; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --lookup-front" ]; then tag=lookup-front; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --fifo-last-state" ]; then tag=fifo-last-state; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --mixed-fast" ]; then tag=mixed-fast; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --mixed-select" ]; then tag=mixed-select; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --return-store" ]; then tag=return-store; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy" ]; then tag=paired-copy; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --slot-copy" ]; then tag=slot-copy; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --material-twin" ]; then tag=material-twin; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --row-range" ]; then tag=row-range; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --row-ceiling" ]; then tag=row-ceiling; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --matrix-four" ]; then tag=matrix-four; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --size-hot" ]; then tag=size-hot; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --cold-scalar" ]; then tag=cold-scalar; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --literal-xmm" ]; then tag=literal-xmm; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --known-difference" ]; then tag=known-difference; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --delta-adjacent" ]; then tag=delta-adjacent; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --rs-prefix" ]; then tag=rs-prefix; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --checkpoint-pack" ]; then tag=checkpoint-pack; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --block-predicate" ]; then tag=block-predicate; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --dispatch-domain" ]; then tag=dispatch-domain; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --gate-sites" ]; then tag=gate-sites; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --scope-floor" ]; then tag=scope-floor; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --model-copy" ]; then tag=model-copy; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --push-scratch" ]; then tag=push-scratch; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --program-range" ]; then tag=program-range; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --icall-local" ]; then tag=icall-local; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --target-switch" ]; then tag=target-switch; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --stack-prefix" ]; then tag=stack-prefix; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --indexed-read" ]; then tag=indexed-read; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --predicate-edge" ]; then tag=predicate-edge; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --header-words" ]; then tag=header-words; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --mesh-edges" ]; then tag=mesh-edges; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --mesh-stage" ]; then tag=mesh-stage; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --paired-entry-slots" ]; then tag=paired-entry-slots; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --material-compare-chain" ]; then tag=material-compare-chain; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --entry-chains" ]; then tag=entry-chains; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --alias-host --alias-words" ]; then tag=alias-words; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --alias-host --guard-host --guard-view" ]; then tag=guard-view; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --material-span" ]; then tag=material-span; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --mesh-trace" ]; then tag=mesh-trace; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --low-words" ]; then tag=low-words; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --rmw-flags" ]; then tag=rmw-flags; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --stack-outline" ]; then tag=stack-outline; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --call-stack" ]; then tag=call-stack; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --effective-mask" ]; then tag=effective-mask; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --light-before" ]; then tag=light-before; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --compact-next" ]; then tag=compact-next; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --timer-mask" ]; then tag=timer-mask; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --simple-layout" ]; then tag=simple-layout; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --reg-base" ]; then tag=reg-base; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --page-bias" ]; then tag=page-bias; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --unordered-branch" ]; then tag=unordered-branch; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --group-copy" ]; then tag=group-copy; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --index-prefetch" ]; then tag=index-prefetch; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --vm-blocks" ]; then tag=vm-blocks; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --row-three" ]; then tag=row-three; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --consumer-bounds" ]; then tag=consumer-bounds; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --batch-index-owner" ]; then tag=batch-index-owner; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --private-tail" ]; then tag=private-tail; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --tree-dispatch" ]; then tag=tree-dispatch; fi
# Directly compare the retained bundle with the default playback build;
# no other arm sets this name, so incremental and absolute results stay separate.
if [ "${NGB_OPEN_BASELINE:-}" = default ]; then
 case "$tag" in model-copy) tag=model-copy-default;; paired-copy) tag=paired-copy-default;; batch-bytes) tag=retained-default;; page-hot-o3) tag=hot-default;; after-regs) tag=after-default;; compact-loops) tag=compact-default;; *) exit 2;; esac
fi
# Measure the marginal benefit of the shared bridge against exactly the same
# 47-unit guest build, separate from the 14-to-47 comparison.
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --shared-pop-tail" ]; then tag=shared-pop-tail; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --hle-scalar-call" ]; then tag=hle-scalar-call; fi
if [ "$*" = "--full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --cmd-service-span" ]; then tag=cmd-service-span; fi
if [ "$tag" = shared-pop-tail ] || [ "$tag" = hle-scalar-call ] || [ "$tag" = cmd-service-span ]; then
 python3 "$p/wide-motion.py" --serial --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy
elif [ "$tag" = guard-view ]; then
 python3 "$p/wide-motion.py" --serial --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --alias-host --guard-host
elif [ "$tag" = alias-words ]; then
 python3 "$p/wide-motion.py" --serial --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy --alias-host
elif [ "$tag" = row-range ] || [ "$tag" = row-ceiling ] || [ "$tag" = matrix-four ] || [ "$tag" = effective-mask ] || [ "$tag" = call-stack ] || [ "$tag" = stack-outline ] || [ "$tag" = rmw-flags ] || [ "$tag" = low-words ] || [ "$tag" = indexed-read ] || [ "$tag" = mesh-edges ] || [ "$tag" = mesh-trace ] || [ "$tag" = material-span ] || [ "$tag" = entry-chains ] || [ "$tag" = material-compare-chain ] || [ "$tag" = paired-entry-slots ] || [ "$tag" = mesh-stage ] || [ "$tag" = header-words ] || [ "$tag" = predicate-edge ] || [ "$tag" = stack-prefix ] || [ "$tag" = target-switch ] || [ "$tag" = icall-local ] || [ "$tag" = program-range ] || [ "$tag" = push-scratch ] || [ "$tag" = model-copy ] || [ "$tag" = scope-floor ] || [ "$tag" = gate-sites ] || [ "$tag" = dispatch-domain ] || [ "$tag" = block-predicate ] || [ "$tag" = checkpoint-pack ] || [ "$tag" = rs-prefix ] || [ "$tag" = delta-adjacent ] || [ "$tag" = known-difference ] || [ "$tag" = literal-xmm ] || [ "$tag" = cold-scalar ] || [ "$tag" = size-hot ] || [ "$tag" = light-before ]; then
 python3 "$p/wide-motion.py" --serial --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops --paired-copy
elif [ "$tag" = material-twin ] || [ "$tag" = slot-copy ] || [ "$tag" = paired-copy ] || [ "$tag" = return-store ] || [ "$tag" = mixed-select ] || [ "$tag" = mixed-fast ] || [ "$tag" = fifo-last-state ] || [ "$tag" = lookup-front ] || [ "$tag" = compact-next ] || [ "$tag" = stream-layout ] || [ "$tag" = header-fold ] || [ "$tag" = batch-handoff ] || [ "$tag" = vblank-window ] || [ "$tag" = entry-mask ] || [ "$tag" = entry-literal ] || [ "$tag" = light-record ] || [ "$tag" = light-zero ] || [ "$tag" = material-inline ] || [ "$tag" = page-bias ] || [ "$tag" = reg-base ] || [ "$tag" = simple-layout ] || [ "$tag" = timer-mask ] || [ "$tag" = checkpoint-loads ] || [ "$tag" = node-page-run ] || [ "$tag" = node-walk ] || [ "$tag" = poll-inline ] || [ "$tag" = tree-tickets ] || [ "$tag" = cmd-target ] || [ "$tag" = fifo-method-table ]; then
 python3 "$p/wide-motion.py" --serial --full-page --command-record --batch-bytes --page-hot-o3 --after-regs --compact-loops
elif [ "$tag" = compact-loops ] || [ "$tag" = index-prefetch ] || [ "$tag" = group-copy ] || [ "$tag" = draw-lto ] || [ "$tag" = simple-literal ] || [ "$tag" = constant-groups ] || [ "$tag" = loop-ira ] || [ "$tag" = vm-blocks ] || [ "$tag" = row-three ] || [ "$tag" = unordered-branch ]; then
 python3 "$p/wide-motion.py" --serial --full-page --command-record --batch-bytes --page-hot-o3 --after-regs
elif [ "$tag" = batch-index-owner ] || [ "$tag" = consumer-bounds ] || [ "$tag" = after-regs ] || [ "$tag" = private-tail ] || [ "$tag" = light-clear ] || [ "$tag" = tree-dispatch ] || [ "$tag" = tree-null ] || [ "$tag" = tree-level ] || [ "$tag" = pc-density ] || [ "$tag" = history-cost ] || [ "$tag" = gate-mapped ] || [ "$tag" = gate-high ] || [ "$tag" = gate-pointer ] || [ "$tag" = fifo-lookahead ] || [ "$tag" = state-witness ] || [ "$tag" = index-equal ] || [ "$tag" = native-draw-o3 ] || [ "$tag" = page-next-o3 ] || [ "$tag" = header-span ]; then
 python3 "$p/wide-motion.py" --serial --full-page --command-record --batch-bytes --page-hot-o3
elif [ "$tag" = page-hot-o3 ] || [ "$tag" = batch-headers ] || [ "$tag" = batch-128 ]; then
 python3 "$p/wide-motion.py" --serial --full-page --command-record --batch-bytes
elif [ "$tag" = batch-bytes ]; then
 python3 "$p/wide-motion.py" --serial --full-page --command-record
elif [ "$variant" = --cmd-page-run ] || [ "$variant" = --cmd-pointer ] || [ "$variant" = --box-inline ] || [ "$variant" = --compact-bridges ] || [ "$variant" = --matrix-row ] || [ "$variant" = --word-page ] || [ "$variant" = --byte-page ] || [ "$variant" = --hot-image-span ] || [ "$variant" = --frame-spans ] || [ "$variant" = --shader-bank ] || [ "$variant" = --hot-entry ] || [ "$variant" = --guest-frame ] || [ "$variant" = --transform-guard ] || [ "$variant" = --contact-axis ] || [ "$variant" = --detail-cost ] || [ "$variant" = --command-record ] || [ "$variant" = --fixed-pieces ] || [ "$variant" = --index-dispatch ] || [ "$variant" = --jump-buckets ] || [ "$variant" = --checkpoint-leaf ] || [ "$variant" = --empty-material ] || [ "$variant" = --matrix-transfer ] || [ "$variant" = --stage-tail ] || [ "$variant" = --round-range ] || [ "$variant" = --product-cache ] || [ "$variant" = --scalar-all ] || [ "$variant" = --scalar-run ] || [ "$variant" = --vector-span ] || [ "$variant" = --fist-round ]; then
 python3 "$p/wide-motion.py" --serial --full-guest
else
 python3 "$p/wide-motion.py" --serial
fi
mv "$d/replay" "$d/original"
python3 "$p/wide-motion.py" --serial "$@"
mv "$d/replay" "$d/limit"
rm -f "$d/replay"
restore_original() {
 if [ -f "$d/original" ]; then
  rm -f "$d/replay"
  mv "$d/original" "$d/replay"
 fi
}
trap restore_original EXIT
if [ "$variant" = --product-cache ]; then
 ln -sf limit "$d/replay"
 NGB_PRODUCT_CHECK=1 sh "$p/run-wide.sh" "$tag-audit"
 grep -Eq '^\[PRODUCT_CHECK\] [1-9][0-9]*$' "$d/$tag-audit.log"
fi
for a in original-1 limit-1 limit-2 original-2 original-3 limit-3 limit-4 original-4; do
 ln -sf "${a%-*}" "$d/replay"
 sh "$p/run-wide.sh" "$tag-$a"
 if [ "$tag" = guard-view ]; then
  # A completion marker alone cannot prove that all 120 measured frames
  # ran with the view active. Reject late activation or early shutdown.
  awk '/^\[GUARD_VIEW\] armed$/{if(state!=0)bad=1;state=1}
       /^\[OPEN_PAIR\] /{if(state!=1 || $2!=++frames)bad=1}
       /^\[GUARD_VIEW\] completed$/{if(state!=1 || frames!=120)bad=1;state=2}
       END{exit (bad || frames!=120 || state!=2)}' "$d/$tag-$a.log"
 fi
 if [ "$tag" = alias-words ]; then grep -qF "[ALIAS_RAM] shared views verified" "$d/$tag-$a.log"; fi
done
restore_original
trap - EXIT
python3 "$p/page-limit-report.py" "$d" "$tag"
python3 "$p/work-match.py" "$d" "$tag"
