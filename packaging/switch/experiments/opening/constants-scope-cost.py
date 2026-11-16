"""Time real game-thread deferred sync, or just the constants inside it, never both at once."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'perf'))
from native_probe import *
p=NativeProbe('opening-constants-scope');p.driver('')
s=(ROOT/'src/d3d/hle.cpp').read_text()
k='void SyncDeferred() {'
assert s.count(k)==1
s=s.replace(k,r'''
static unsigned cs_frame,cs_rng=16917;
static unsigned long long cs_stat[2][2][5];
static uint64_t cs_clock(){timespec t;if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t))std::abort();return uint64_t(t.tv_sec)*1000000000+t.tv_nsec;}
extern "C" void cs_boundary(unsigned f){
 if(f==30||f==120){for(unsigned a=0;a<2;a++)for(unsigned b=0;b<2;b++){auto &x=cs_stat[a][b];
 fprintf(stderr,"[CS_COST] %u %u %u %llu %llu %llu %llu %llu\n",f,a,b,x[0],x[1],x[2],x[3],x[4]);}memset(cs_stat,0,sizeof(cs_stat));}
 cs_frame=f<120?f+1:0;
}
'''+k+r'''
 unsigned cs_mode=9;uint64_t cs_start=0,cs_elapsed=0;
 if(cs_frame){cs_rng=1664525u*cs_rng+1013904223u;cs_mode=cs_rng>>29;}
 if(cs_mode==0)cs_start=cs_clock();else if(cs_mode==1){auto t=cs_clock();cs_elapsed=cs_clock()-t;}
''')
k='    SyncDrawConstants();'
assert s.count(k)==1
s=s.replace(k,r'''    if(cs_mode==2)cs_start=cs_clock();else if(cs_mode==3){auto t=cs_clock();cs_elapsed=cs_clock()-t;}
'''+k+'\n    if(cs_mode==2)cs_elapsed=cs_clock()-cs_start;')
k='\n}\n\ngpu::Surface SurfaceOf'
assert s.count(k)==1
s=s.replace(k,r'''
    if(cs_mode==0)cs_elapsed=cs_clock()-cs_start;
    if(cs_frame){unsigned b=g_state.changed_constant_blocks!=0;
    for(auto &arm:cs_stat)++arm[b][0];
    if(cs_mode<4){auto &x=cs_stat[cs_mode/2][b];unsigned off=cs_mode%2?3:1;++x[off];x[off+1]+=cs_elapsed;}}
'''+k)
p.add('hle.cpp','#include <time.h>\n'+s)
s=(RUNTIME/'scene/bridge.c').read_text()
for k,f in [('            ngb_direct_reset_stats();','0'),('    ++scene_flips;','scene_flips')]:
 assert s.count(k)==1;s=s.replace(k,k+' extern void cs_boundary(unsigned);cs_boundary('+f+');')
p.add('scene/bridge.c',s);p.link.insert(1,'-Wl,--strip-debug');p.finish()
