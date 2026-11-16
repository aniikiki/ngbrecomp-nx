#!/usr/bin/env bash
# Run from the checkout, after building host and switch with the same staged XBE.
set -euo pipefail
cd "$(dirname "$0")/../../.."
toolsdir=packaging/switch/perf
build=build/switch-runtime
out=$build/core-perf
mkdir -p "$out"
host(){ docker run --rm -v "$PWD":/work -w /work "${NGB_PERF_HOST_IMAGE:-ngb-switch-host:direct0331}" "$@"; }
cross(){ docker run --rm -v "$PWD":/work -v "${NGB_NXVK_ROOT:-$PWD/../nxvk}":/nxvk:ro -w /work "${NGB_PERF_SWITCH_IMAGE:-ngb-switch-nxvk:dev}" "$@"; }
combat(){
    host sh -eu -c '
        p=build/switch-runtime
        export NGB_TEST_IDLE_SCENE=combat XDG_CACHE_HOME=/work/$p/direct/mesa-cache LP_NUM_THREADS=4
        export NGB_DIRECT_SPIRV=/work/$p/direct/cache/spirv.bin VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json
        "$1" --start-button "$p/romfs" "$(mktemp -d)"
    ' sh "$1" > "$out/$2.log" 2>&1
    grep -Fq "[RESULT] status=1 reason=verified original combat window" "$out/$2.log"
    grep '^\[OFFLINE\]' "$out/$2.log"
}
case "${1:-baseline}" in
    baseline)
        host python3 "$toolsdir/exact.py"
        host "$out/exact" game_files/default.xbe
        combat "$out/exact" exact ;;
    story|story-tasks)
        mode=$1
        host sh -eu -c '
            ninja -C build/switch-runtime/host -j3 ngb-runtime-test
            python3 packaging/switch/perf/exact.py
            bin=build/switch-runtime/core-perf/exact
            if [ "$1" = story-tasks ]; then
                python3 packaging/switch/perf/tasks.py --story
                bin=build/switch-runtime/core-perf/story-tasks/replay
            fi
            export NGB_TEST_STORY=1 LP_NUM_THREADS=4
            export XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
            export NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin
            export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json
            "$bin" --start-button game_files "$(mktemp -d)"
        ' sh "$mode" > "$out/$mode.log" 2>&1
        grep -Fq '[RESULT] status=1 reason=verified first chapter player control' "$out/$mode.log"
        if [ "$mode" = story-tasks ]; then
            python3 "$toolsdir/task-report.py" "$out/$mode.log" --story
        else
            grep -E '^\[(STORYCPU|RESULT)\]' "$out/$mode.log"
        fi ;;
    mesh-calls)
        host python3 "$toolsdir/mesh-calls.py"
        combat "$out/mesh-calls/replay" mesh-calls
        python3 "$toolsdir/mesh-call-report.py" "$out/mesh-calls.bin" ;;
    pc)
        host python3 "$toolsdir/sample-pc.py"
        combat "$out/sample-pc/replay" sample-pc
        host python3 "$toolsdir/report-pc.py" "$out/sample-pc/replay" "$out/sample-pc.log" ;;
    train)
        cross python3 "$toolsdir/pgo.py" train
        host python3 "$toolsdir/pgo-link.py" train
        combat "$out/train" train
        grep -Fq '[TRAIN] wrote 14 profiles' "$out/train.log"
        cross python3 "$toolsdir/pgo.py" guided
        host python3 "$toolsdir/pgo-link.py" guided
        combat "$out/guided" guided ;;
    tasks|children)
        name=tasks
        opts=()
        if [ "$1" = children ]; then
            name=task-children
            cross python3 "$toolsdir/task-children.py"
            opts+=(--children)
        fi
        host python3 "$toolsdir/tasks.py" "${opts[@]}"
        combat "$out/$name/replay" "$name"
        python3 "$toolsdir/task-report.py" "$out/$name.log" ;;
    pair|scheduler)
        group=pgo
        if [ "$1" = scheduler ]; then group=scheduler; fi
        host python3 "$toolsdir/pair.py" "$group"
        combat "$out/pair-$group/replay" "pair-$group"
        python3 "$toolsdir/analyze-pair.py" "$out/pair-$group.log" ;;
    *) echo "usage: bash $0 [baseline|train|pair|scheduler|tasks|children|story|story-tasks|pc|mesh-calls]" >&2; exit 2 ;;
esac
