"""Audit and A/B the per-draw method-table decode on the original 120 opening flips."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'perf'))
from native_probe import NativeProbe, ROOT, RUNTIME
p=NativeProbe('opening-setup')
s=(ROOT/'src/d3d/hle.cpp').read_text()
start=s.index('    for (uint32_t i = 0; i < gpu::kRsDeferredFirst; i++)')
end=s.index('    for (int s = 0;',start)
old=s[start:end]
s='extern "C" { extern unsigned plan_mode; unsigned plan_calls,plan_builds,plan_stores,plan_runs; }\n'+s[:start]+'''    if(plan_mode){
        constexpr unsigned N=gpu::kRsDeferredFirst;
        struct Run { unsigned src,dst,n; };
        static struct { bool valid; unsigned words[N],num,stores; Run runs[N]; } p{};
        if(!p.valid || std::memcmp(p.words,methods,sizeof p.words)){
            p.valid=true;p.num=p.stores=0;std::memcpy(p.words,methods,sizeof p.words);
            for(unsigned i=0;i<N;i++){
                unsigned m=methods[i]&0x1ffc;
                if(!((m>=0x300 && m<0x400)||m==0x1d78))continue;
                unsigned dst=m>>2;
                if(p.num && p.runs[p.num-1].src+p.runs[p.num-1].n==i && p.runs[p.num-1].dst+p.runs[p.num-1].n==dst)++p.runs[p.num-1].n;
                else p.runs[p.num++]={i,dst,1};
                ++p.stores;
            }
            ++plan_builds;
        }
        auto apply=[&](){
          for(unsigned i=0;i<p.num;i++){auto r=p.runs[i];if(r.n==1)g_state.simple[r.dst]=states[r.src];else std::memcpy(&g_state.simple[r.dst],states+r.src,4*r.n);}
        };
        if(plan_mode==2){
           auto expected=g_state.simple;
           for(unsigned i=0;i<N;i++){auto m=methods[i]&0x1ffc;if((m>=0x300 && m<0x400)||m==0x1d78)expected[m>>2]=states[i];}
           apply();if(expected!=g_state.simple)std::abort();
           ++plan_calls;plan_stores+=p.stores;plan_runs+=p.num;
        }else apply();
    }else
'''+old+s[end:]
p.add('hle.cpp',s)
p.driver(r'''
unsigned plan_mode;extern unsigned plan_calls,plan_builds,plan_stores,plan_runs;
void plan_flip(unsigned f,unsigned draws){
 static uint64_t last;static unsigned prev;struct timespec t;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);
 uint64_t now=t.tv_sec*1000000000ull+t.tv_nsec;
 if(f && last)fprintf(stderr,"[OPEN_PAIR] %u %u %llu %u\n",f,plan_mode,(unsigned long long)(now-last),draws-prev);
 if(f==120)fprintf(stderr,"[PLAN] verified=%u builds=%u stores=%u runs=%u\n",plan_calls,plan_builds,plan_stores,plan_runs);
 plan_mode=f>=120?0:getenv("NGB_PLAN_CHECK")?2:(((f/2+12345)*2654435761u>>31)^(f&1)^(getenv("NGB_OPEN_REVERSE")!=NULL));
 last=now;prev=draws;
}
''')
s=(RUNTIME/'scene/bridge.c').read_text()
for k,f in [('            ngb_direct_reset_stats();','0'),('    ++scene_flips;','scene_flips')]:
 assert s.count(k)==1;s=s.replace(k,k+f' extern void plan_flip(unsigned,unsigned);plan_flip({f},draws);')
p.add('scene/bridge.c',s);p.link.insert(1,'-Wl,--strip-debug');p.finish()
