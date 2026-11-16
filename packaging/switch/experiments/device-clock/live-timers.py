"""Measure active timer dispatch on alternating complete game frames. Both arms
share the actual timers, including mutations from in-progress callbacks."""
from pathlib import Path
import sys
h=Path(__file__).resolve().parent;perf=h.parents[1]/'perf';sys.path.insert(0,str(perf))
from native_probe import *
p=NativeProbe('live-timers')
s=(h/'active-timers.c').read_text()
a=s.index('    /* A callback may arm')
s=s[:a]+'''    extern unsigned trial_variant;
    if(!trial_variant){
        for(unsigned i=0;i<32;i++){
            if(!timers[i].armed || now<timers[i].due)continue;
            uint64_t period=timers[i].period;
            if(period)timers[i].due=period>UINT64_MAX-now?UINT64_MAX:now+period;
            else {timers[i].armed=0;armed_mask &= ~(UINT32_C(1)<<i);}
            fire(timers[i].address,timers[i].dpc,period!=0);
        }return;
    }
'''+s[a:]
o=p.compile('timers.c',s);p.link[p.link.index(next(k for k in p.link if k.endswith('/timers.c.o')))]=o
s=(REGS/'host-runtime.inc').read_text();tag='if (interrupt_enabled && !delivering_callback && MEM8(g_fs_base + 0x24) < 2) {'
assert s.count(tag)==1
s=s.replace(tag,'extern int ngb_timers_active(void);extern unsigned trial_variant;\n    '+tag.replace('if (','if ((!trial_variant || ngb_timers_active()) && '))
(p.out/'host-runtime.inc').write_text(s)
p.driver((perf/'trial.inc').read_text());s=(RUNTIME/'scene/bridge.c').read_text();k='    ++scene_flips;'
p.add('scene/bridge.c',s.replace(k,k+' extern void ngb_trial_flip(unsigned,unsigned);ngb_trial_flip(scene_flips,draws);'));p.finish()
