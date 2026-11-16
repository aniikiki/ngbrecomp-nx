"""Use a one-pass ARM change mask for the 1336-byte render-state range."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'perf'))
from native_probe import NativeProbe, ROOT, RUNTIME
p=NativeProbe('opening-delta-mask')
s=(ROOT/'src/d3d/gpu/threaded.cpp').read_text()
anchor='        // These fixed-size comparisons fold'
assert s.count(anchor)==1
s='#include <arm_neon.h>\nextern "C" {extern unsigned dm_mode,dm_checked,dm_changed;}\n'+s.replace(anchor,Path(__file__).with_name('delta-mask.inc').read_text()+anchor)
p.add('threaded.cpp',s)
p.driver('''
unsigned dm_mode,dm_checked,dm_changed;
void fixed_frame(unsigned f,unsigned draws){
 static uint64_t last;static unsigned previous;
 struct timespec t;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);
 uint64_t now=t.tv_sec*1000000000ull+t.tv_nsec;
 if(f && last)fprintf(stderr,"[OPEN_PAIR] %u %u %llu %u\\n",f,dm_mode,(unsigned long long)(now-last),draws-previous);
 if(f==120)fprintf(stderr,"[DM] %u %u\\n",dm_checked,dm_changed);
 dm_mode=f>=120?0:getenv("NGB_OPEN_CHECK")?2: ((((f/2+12345)*2654435761u>>31)^(f&1))^(getenv("NGB_OPEN_REVERSE")!=NULL));
 last=now;previous=draws;
}
''')
s=(RUNTIME/'scene/bridge.c').read_text()
for k,f in [('            ngb_direct_reset_stats();','0'),('    ++scene_flips;','scene_flips')]:
 assert s.count(k)==1
 s=s.replace(k,k+f' extern void fixed_frame(unsigned,unsigned);fixed_frame({f},draws);')
p.add('scene/bridge.c',s);p.link.insert(1,'-Wl,--strip-debug');p.finish()
