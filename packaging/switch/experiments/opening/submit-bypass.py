"""Host counterfactual. Measure Draw entry -> backend return; never skip guest push/fence or visibility calls."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'perf'))
from native_probe import NativeProbe,ROOT,RUNTIME
p=NativeProbe('opening-submit-bypass')
def add(s,k,v):
 assert s.count(k)==1,k
 return s.replace(k,v)
s=(RUNTIME/'direct/hooks.c').read_text()
k='void ngb_direct_mesh_scope(int enter)\n{'
s=add(s,k,'extern void bp_mesh(unsigned);\n'+k+'\n if(enter)bp_mesh(MEM32(esp+4));')
p.link[p.link.index(str(p.core/'exact-hooks.c.o'))]=p.compile('direct/hooks.c',s,['-include',str(RUNTIME/'switch_guest_regs.h')])
s=(ROOT/'src/d3d/hle.cpp').read_text()
s='extern "C"{int bp_draw(unsigned,unsigned,unsigned,const unsigned char*);extern unsigned bp_vis,bp_active;unsigned long long bp_cpu();extern unsigned long long bp_sum;}\n'+s
k='    if (!g_backend) return;\n    bool measure'
s=add(s,k,'''    if (!g_backend) return;
    if(bp_draw(prim,start,count,indices))return;
    auto bp_begin=bp_active && !bp_vis ? bp_cpu():0;
    bool measure''')
k='    if (measure) ngb_direct_draw_time'
s=add(s,k,'    if(bp_begin)bp_sum+=bp_cpu()-bp_begin;\n'+k)
k='    if (g_backend && !g_mirror) g_backend->VisibilityBegin();'
s=add(s,k,'    bp_vis=1;\n'+k)
k='case D3DF_D3DDevice_EndVisibilityTest: {'
s=add(s,k,k+'\n        bp_vis=0;')
p.add('hle.cpp',s)
p.driver(r'''
unsigned bp_active,bp_vis;
static unsigned bp_mode,bp_n,bp_meshes,bp_skips;static uint64_t bp_m,bp_d;
unsigned long long bp_sum;
unsigned long long bp_cpu(void){struct timespec t;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);return 1000000000ull*t.tv_sec+t.tv_nsec;}
static uint64_t bp_mix(uint64_t h,uint32_t x){return (h^x)*1099511628211ull;}
void bp_mesh(unsigned mesh){if(bp_active){++bp_meshes;bp_m=bp_mix(bp_m,mesh);bp_d=bp_mix(bp_mix(bp_d,0x4d),mesh);}}
int bp_draw(unsigned prim,unsigned start,unsigned count,const unsigned char *indices){
 if(!bp_active)return 0;
 ++bp_n;bp_d=bp_mix(bp_mix(bp_mix(bp_mix(bp_d,prim),start),count),!!indices);
 if(indices){for(unsigned i=0;i<count;i++){uint16_t v;memcpy(&v,indices+2*i,2);bp_d=bp_mix(bp_d,v);}}
 if(bp_mode&&!bp_vis){++bp_skips;return 1;}return 0;
}
void bp_flip(unsigned f){
 static unsigned long long last;unsigned long long now=bp_cpu();
 if(bp_active)fprintf(stderr,"[BYPASS] %u %u %u %u %016llx %016llx %u %llu %llu\n",f,bp_mode,bp_meshes,bp_n,(unsigned long long)bp_m,(unsigned long long)bp_d,bp_skips,now-last,bp_sum);
 bp_active=f>=30 && f<120;bp_mode=getenv("NGB_BYPASS")!=NULL;
 bp_m=bp_d=14695981039346656037ull;bp_n=bp_meshes=bp_skips=0;bp_sum=0;last=bp_cpu();
}
''')
s=(RUNTIME/'scene/bridge.c').read_text()
k='    ++scene_flips;'
p.add('scene/bridge.c',add(s,k,k+' extern void bp_flip(unsigned);bp_flip(scene_flips);'))
p.link.insert(1,'-Wl,--strip-debug');p.finish()
