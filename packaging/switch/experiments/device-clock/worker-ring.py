"""Walk the actual Xbox runnable ring without a dynamic integer division or
a second full scan. Keep current event reads, ordering, and fallback worker."""
from pathlib import Path
import sys
h=Path(__file__).resolve().parent;perf=h.parents[1]/'perf';sys.path.insert(0,str(perf))
from native_probe import *
p=NativeProbe('worker-ring');p.link.insert(1,'-Wl,--strip-debug')
s=(RUNTIME/'workers.inc').read_text()
a=s.index('static unsigned next_worker(');b=s.index('static void yield_worker(',a)
orig=s[a:b];fast=orig.replace('next_worker(', 'next_worker_ring(').replace('for (unsigned n = 1; n < thread_count; ++n) {\n        unsigned i = (running_worker + n) % thread_count;', '''unsigned i=running_worker;
    for (;;) {
        if (++i==thread_count)i=0;
        if (i==running_worker)break;''')
s=s[:a]+orig.replace('next_worker(', 'next_worker_ref(')+fast+'''extern unsigned trial_variant;
static unsigned next_worker(uint64_t now){return trial_variant?next_worker_ring(now):next_worker_ref(now);}\n'''+s[b:]
(p.out/'workers.inc').write_text(s);(p.out/'host-runtime.inc').write_text((REGS/'host-runtime.inc').read_text())
p.driver((perf/'trial.inc').read_text())
s=(RUNTIME/'scene/bridge.c').read_text();k='    ++scene_flips;';p.add('scene/bridge.c',s.replace(k,k+' extern void ngb_trial_flip(unsigned,unsigned);ngb_trial_flip(scene_flips,draws);'));p.finish()
