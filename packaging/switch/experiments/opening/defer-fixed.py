"""Skip guest program-register sync for three fixed-FVF triangle-strip formats.
Always resync from live guest memory on the next consuming programmable draw."""
from pathlib import Path
import sys
h=Path(__file__).resolve().parent;sys.path.insert(0,str(h.parents[1]/'perf'))
from native_probe import *
p=NativeProbe('opening-defer-fixed')
s='extern "C"{extern unsigned df_mode;unsigned df_skip,df_check;}\n'+(ROOT/'src/d3d/hle.cpp').read_text()
k='void SyncDeferred()';assert s.count(k)==1;s=s.replace(k,'void SyncDeferred(bool skip_bank)')
k='    SyncDrawConstants();';assert s.count(k)==1;s=s.replace(k,'    if(!skip_bank)SyncDrawConstants();')
k='    SyncDeferred();';assert s.count(k)==1;s=s.replace(k,r'''
    bool fixed=df_mode && prim==6 && (g_state.vs_handle==0x142 || g_state.vs_handle==0x152 || g_state.vs_handle==0x112);
    if(fixed)++df_skip;
    SyncDeferred(fixed);
    if(df_mode==2 && !fixed){
        for(unsigned i=0;i<192;i++){
            std::array<float,4> sc,ofs;ViewportConstants(sc,ofs);
            const void *ref=i==58?(const void*)sc.data():i==59?(const void*)ofs.data():HostPtr(kVsConstants+16*i);
            if(std::memcmp(g_state.vsc[i].data(),ref,16))std::abort();
        }++df_check;
    }
''')
p.add('hle.cpp',s)
p.driver(r'''
extern unsigned df_skip,df_check;unsigned df_mode;
void df_flip(unsigned f,unsigned draws){
 static uint64_t last;static unsigned prev;struct timespec t;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);uint64_t now=t.tv_sec*1000000000ull+t.tv_nsec;
 if(f&&last)fprintf(stderr,"[OPEN_PAIR] %u %u %llu %u\n",f,df_mode,(unsigned long long)(now-last),draws-prev);
 if(f==120)fprintf(stderr,"[DEFER] %u %u\n",df_skip,df_check);
 df_mode=f>=120?0:getenv("NGB_OPEN_CHECK")?2:(((f/2+12345)*2654435761u>>31)^(f&1)^(getenv("NGB_OPEN_REVERSE")!=NULL));last=now;prev=draws;}
''')
s=(RUNTIME/'scene/bridge.c').read_text()
for k,f in [('            ngb_direct_reset_stats();','0'),('    ++scene_flips;','scene_flips')]:
 assert s.count(k)==1;s=s.replace(k,k+f' extern void df_flip(unsigned,unsigned);df_flip({f},draws);')
p.add('scene/bridge.c',s);p.link.insert(1,'-Wl,--strip-debug');p.finish()
