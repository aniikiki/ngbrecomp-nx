"""Replace the second scan of changed fixed state with one complete range delta."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'perf'))
from native_probe import NativeProbe, ROOT, RUNTIME
p=NativeProbe('opening-setup')
s=(ROOT/'src/d3d/gpu/threaded.cpp').read_text()
anchor='        if constexpr (r.len <= kPiece) WriteDelta(r.off, now, r.len);'
assert s.count(anchor)==1
s='extern "C" {extern unsigned fixed_arm; }\n'+s.replace(anchor,'''        if (fixed_arm && r.len > kPiece) {
            WriteDelta(r.off,now,r.len);
            return;
        }
'''+anchor)
p.add('threaded.cpp',s)
p.driver('''
unsigned fixed_arm;
void fixed_frame(unsigned f,unsigned draws){
 static uint64_t last;static unsigned previous;
 struct timespec t;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);
 uint64_t now=t.tv_sec*1000000000ull+t.tv_nsec;
 if(f && last)fprintf(stderr,"[OPEN_PAIR] %u %u %llu %u\\n",f,fixed_arm,(unsigned long long)(now-last),draws-previous);
 fixed_arm=f<120 && ((((f/2+12345)*2654435761u>>31)^(f&1))^(getenv("NGB_OPEN_REVERSE")!=NULL));
 last=now;previous=draws;
}
''')
s=(RUNTIME/'scene/bridge.c').read_text()
for k,f in [('            ngb_direct_reset_stats();','0'),('    ++scene_flips;','scene_flips')]:
 assert s.count(k)==1
 s=s.replace(k,k+f' extern void fixed_frame(unsigned,unsigned);fixed_frame({f},draws);')
p.add('scene/bridge.c',s);p.link.insert(1,'-Wl,--strip-debug');p.finish()
