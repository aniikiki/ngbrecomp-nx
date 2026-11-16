# Offline trials with the Switch guest code

Build the Linux/AArch64 host test and Switch NRO from the same staged game image first. From the repository root, run:

```sh
bash packaging/switch/perf/replay.sh baseline
bash packaging/switch/perf/replay.sh scheduler
```

The baseline relinks the Linux test using every generated guest object from the devkitA64 Switch build (including dispatch). The host's bridge, register storage and generated guest code must agree on the register ABI. Only the three register-file consumers are rebuilt on the host; Linux supplies its own thread pointer for the guest's remaining TLS. The baseline runs the bridge tests and then follows the original title timer into combat. A successful combat test must observe movement and reach flip 1920. The software Vulkan renderer, OS and CPU are still the host's. This is not a Switch FPS estimate.

The scheduler trial changes the ready-worker policy in one process at frame boundaries. Each adjacent pair gets one frame of either variant, with a fixed balanced order. The report covers frames 33–120 and two consecutive 120-frame windows at 1681–1920. It includes thread CPU time, draw count, function entries and polls for both sides. An eight-frame block bootstrap gives a rough uncertainty interval, not a hardware forecast. Trials with a changed amount of game work or unusual contention need repeating. For a comparison of independent runs, disable instrumentation and also inspect the `[OFFLINE]` totals (end=120 spans 90 frames; end=1800 and 1920 each span 120).

An optional experiment trains GCC on the same game code:

```sh
bash packaging/switch/perf/replay.sh train
bash packaging/switch/perf/replay.sh pair
```

The cross compiler emits freestanding GCC counters in 14 units. On normal exit the host runner uses the **cross compiler's libgcov** to write the profiles, then devkitA64 recompiles the same units. Missing profiles and control-flow mismatches fail the build. No instrumented code, profile counters, training data, temporary saves or alternate code paths are installed on the console. All generated files live under `build/switch-runtime/core-perf`; the container removes temporary saves when it exits. Re-run baseline and train after changing guest code. Run timed trials one at a time. Override the local Docker image names with `NGB_PERF_HOST_IMAGE` and `NGB_PERF_SWITCH_IMAGE` if needed.

After baseline, the `tasks` mode charges thread CPU time to the callback in the game's own task object, saving and restoring the attribution at Xbox worker and fiber switches. Interrupt/DPC callbacks get a separate bucket; the scheduler and unidentified code remain visible. Each window must reconcile to the outside frame clock within 2% or 2 ms total. The `children` mode recompiles four guest units with devkitA64, marking the direct children of the three biggest update tasks and the indirect callbacks in the render list. It replaces the parent's time with the child's time while that child is running. Its extra clock reads perturb absolute timings; use the uninstrumented frame trial for performance claims.

For actual gameplay, run `bash packaging/switch/perf/replay.sh story` with the
matching full extracted disc at `game_files/`. This test starts New Game from
the title, lets the original movies run, and records the player position while
delivering neutral, right, neutral and left inputs through the guest USB pad.
It requires two consecutive successful reversals after a stationary start.
The trace and game-thread CPU windows are in `core-perf/story.log`; saves live
only in the temporary container. The CPU windows exclude software Vulkan worker
threads and do not measure console FPS.

`story-tasks` repeats the chapter test with exclusive task clocks over two
120-frame windows at the transition to player control. After `baseline`, use
`pc` to sample native ARM instructions across attract-mode frames 1681–1920.
The timer counts only CPU time on the game thread and sends signals to that
thread. Symbolize with the exact ELF and libraries inside the runner image;
no addresses or timers are installed on Switch.

Since 0.49.0, detailed guest draw and material timings cover one complete frame per sixteen, with a rotating phase. Frame intervals, draw and submission counts, and the game-thread CPU measurement still cover every frame. Divide sampled time by the reported sampled frame count. For an offline full-timing control, run the same replay binary with NGB_RENDER_FULL_TIMING=1 in its environment.

After baseline, `mesh-calls` traces the ordered Direct3D interception sites for
each outermost original mesh submission over combat frames 1801–1920. It also
counts submissions without interceptions. Same-mesh comparisons pair the nth
occurrence of a mesh pointer in successive frames. A matching sequence says
nothing about argument values, vertex data, or render state. Direct material
fast paths bypassing the interception hook are intentionally excluded.

To inspect where the packaged CPU spends its time, use
`arm-registers/host-check.py --stack` in the host container. Run the resulting
`native-regs/stack-check` with the same combat inputs; run `report-stack.py`
with that exact ELF and replay log. It samples the guest thread's CPU timer,
walking at most 8 KiB of each interrupted ARM stack. Leaf functions without
frame records and truncated outer stacks may be absent. Inclusive child paths
are not additive CPU measurements.

For a draw coverage experiment after baseline, build `visibility-work.py` and
replay `core-perf/visibility-work/replay`. One in seven eligible Vulkan draws
gets an independent query. Original visibility queries keep their own slots.
The renderer samples the producer's concurrent flip count, so the endpoints
can differ from a strictly synchronized frame boundary. A zero query result
is not proof that a draw can be deleted: stencil fail/depth fail operations
may matter, and the result need not repeat on another frame.

`visibility-work.py --compare-cull` pairs each sample with a second draw with
backface culling and attachment writes disabled. `--bounds` and
`--bounds --planes` pair CPU predictions with original GPU coverage and
clipping statistics. Run `bounds-report.py LOG` to reject any contradicted
prediction. `--cut-trial --planes` alternates actual skipping on the renderer
only; `cut-report.py LOG` measures renderer CPU between the first draw and
Present, not whole-game frame time. After `host-check.py --rigid-clip`,
`visibility-work.py --certify` checks every release-positive draw reaching the
actual draw command in the diagnostic window on the packaged game core.
Only the isolated host runs allocate additional Vulkan queries. To measure
the game-thread cost per whole clipped mesh, build `mesh-clip-work.py`, replay
`core-perf/mesh-clip/replay`, then run `mesh-clip-report.py core-perf` using
the absolute or relative path to that build directory. The two binary traces
stay there; a missing command invalidates the comparison.

For a private 0.51 ARM object build, `record-cost.py` (host container) builds the
intact draw scope sampler under core-perf/record-cost. Run the normal combat
replay, then `python3 record-report.py LOG`. Each draw can time at most one
scope. `submission-cost.py` is a **pixel-destructive diagnostic**; deleting
host draws changes queue timing and original task work, so do not interpret
its paired whole-frame difference as saved producer cost.

To attribute guest RAM values across original tasks, run `flow/compile.py`
inside the Switch cross image, then `pair.py task-flow` inside the ARM host
image. The unit is a byte **read event**, not a unique value or elapsed time.
Replay core-perf/pair-task-flow/replay and resolve the resulting log with
`flow-report.py LOG NM`, where NM is `nm -n -S --defined-only` of **that**
executable. The report rejects incomplete windows, dropped sites, and
inconsistent edge/site totals. Runtime callbacks and uninstrumented library
operations are not covered. Do not use instrumented timings as CPU estimates.

After compiling all 47 flow units, host modes `pair.py task-path`,
`pair.py task-chain`, and `pair.py task-versions` run different offline
dependency models over frames 1801–1812. Use ordinary combat replay for
each, then `flow/chain-report.py STRICT RAW VERSIONS SYMBOLS`, with SYMBOLS
from `nm -n` on the **task-chain** executable. It checks complete windows and
reconstructs each critical path length. These count original observed RAM
operations, not hardware cycles. Only the four policies within the versions
replay see the exact same execution. The other runs can have different audio
or guest scheduling work under instrumentation.

For iteration-level attribution, cross-build `flow/actor-cross.py` after
`flow/compile.py`. The host's `pair.py actor-flow` instruments the actor
loop at 1CC5F0 and the sorted actor loop at 147ECD. Keep instrumentation
resident across guest fiber resumes; only collect at flips 1801–1812.
`flow/actor-report.py LOG SYMBOLS` resolves the critical joins. Use the
matching executable's `nm -n` output. `actor-inputs` is a different replay
comparing external first reads to a common snapshot; summarize it using
`flow/actor-input-report.py LOG`. These traces exclude uninstrumented
memory accesses and have no intrinsic cost in milliseconds.

Modes `actor-tx` and `actor-batch` validate observed reads/final writes and
estimate bounded scheduling with no speculative mutation of the original
game. `actor-worker` replays the recorded byte operations on two actual
host workers as a dependency diagnostic; the writes supplied to this
diagnostic are recorded values, not freshly computed results. Conversely,
`actor-fork` and `actor-snapshot` run the original ARM functions in isolated
Linux processes and compare independently computed writes and registers.
Children never commit to the live game. Neither Linux fork nor recorded
outputs are Switch implementation strategies. Measure actual CPU ranges
separately with `flow/actor-clock.py cross|link` and
`flow/actor-stage2.py cross|link`, cross image first, host image second.
