The Switch cross compiler builds a reentrant worker containing only the 69
game functions reached in offline captures. Unknown calls or unsupported
memory access abort the worker job, never call the shared game runtime. The
object depends only on thread-local storage, C memory and math functions,
and setjmp/longjmp. Native or kernel side effects are not allowed.

1. Build the 47-unit flow probe followed by actor-cross.py and the actor-code
   replay. Use flow/native-code-report.py LOG GEN MANIFEST. Keep game data,
   RAM snapshots and manifests under the local ignored build directory.
2. In the devkit container, run build.py MANIFEST (full private image) then
   sparse.py MANIFEST (512 private page slots per worker). The original game
   source and both generated worker sources stay in the ignored build tree.
3. In the ARM host container, run perf/pair.py actor-native or actor-capture,
   then the standard combat replay. The capture variant writes compressed
   job inputs and reference outputs locally. A worker must never write the
   RAM image still executing the reference game.
4. Run replay-sparse.py and bench.py in that host container. Feed the resulting
   replay or bench two private job files. The benchmark compares the same two
   captured jobs serially and concurrently on a persistent thread. Its final
   comparison includes all original written bytes, changed pages, and the
   complete guest register file. Pass the output to bench-report.py.

This is a compute prototype. Correct speculative publication still requires
validated live inputs, serial ordering, original callback execution, and a
fallback on conflict. The paired microbenchmark is not an in-game FPS number.

predict.py compares whole input, stack, world and register substitutions; the
second argument must be from the same traversal as the first (the scene flip
can change within a traversal). The actor-wave mode of perf/pair.py uses
wave.c to start two real native workers before the reference game reaches
the predicted actors. They only write private 4 KiB pages. Its verifier
compares every observed original write and detects additional changed bytes
on every private page. Start with zero used/index entries; a preseeded stack
page must have a matching one-based index, touched entry, and used count.

For the footprint-aware wave, compile sparse.py MANIFEST --footprint before
perf/pair.py actor-wave; run the normal combat replay, optionally with
NGB_WAVE_BENCH=1, and report.py LOG. This starts with one full training image,
then copies only observed pages. Missing pages abort the experiment's job.
The first five successor tasks are independent for the observed traversal;
later tasks wait for their predecessor's registers and stack. That observed
schedule is not a general game invariant.

checkpoint-build.py and journal-build.py build two diagnostic objects with
private poll-state capture. Link via perf/pair.py actor-boundary / actor-journal
respectively and run the full combat replay. journal-report.py compares actual
due-interrupt register snapshots and per-boundary written bytes. These
verifiers deliberately run the original guest, never commit ahead-of-time
worker output, and do not belong in a playable NRO.

replay-journal.py rebuilds captured memory from the ordered write events;
packed-replay.py checks a compact publication format, deliberately mutating
neighboring bytes between intervals. --consume on flow/actor-cross.py adds
a hook to skip the original three calls. perf/pair.py actor-consume uses this
only for a short actor with enough polls until the next callback. The optional
actor-stress mode is an offline conflict stress test, not a supported game
runtime. It restores register state and runs the normal poll service for each
boundary. No verifier belongs in a playable NRO.

For the worker-object journal, generic sanitizer hooks alone miss library
copies: compile journal-build.py with the explicit journal_copy/journal_set
wrappers. Accounting must also expand optimized multi-poll helpers to obtain
precise intermediate guest state. Compact records include a per-word byte
mask. See live-report.py for the actual replacement count in a completed
combat replay, not the number of shadow jobs started.
