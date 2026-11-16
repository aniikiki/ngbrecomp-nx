"""Opening only. Exclusive, contiguous timestamps on sampled Xbox DrawIndexedVertices calls."""
from pathlib import Path
import sys
h=Path(__file__).resolve().parent;sys.path.insert(0,str(h.parents[1]/'perf'))
from native_probe import *
single='--single' in sys.argv
p=NativeProbe('opening-index-single' if single else 'opening-index-ledger');p.driver('')
def edit(s,k,v):assert s.count(k)==1,k;return s.replace(k,v)
# Cheap architectural timer, same thread from entry to return. This is elapsed time, not CPU cycles.
s=(RUNTIME/'direct/hooks.c').read_text()
k='int d3d_hook(int fn)'
s=edit(s,k,r'''
static unsigned ix_f,ix_depth,ix_calls,ix_taken,ix_id,ix_nested,ix_cross,ix_rng=13579;
unsigned ix_on;
static uint64_t ix_edge,ix_start,ix_local[10],ix_ns[10],ix_wall,ix_ticks;
static inline uint64_t ix_now(void){uint64_t t;__asm__ volatile("isb; mrs %0,cntvct_el0":"=r"(t)::"memory");return t;}
void ix_stage(unsigned id){if(!ix_on)return;uint64_t t=ix_now();ix_local[ix_id]+=t-ix_edge;ix_edge=t;ix_id=id;}
static void ix_enter(void){
 if(ix_depth++){++ix_nested;ix_on=0;return;} if(!ix_f)return;++ix_calls;
 ix_rng=1664525u*ix_rng+1013904223u;if(ix_rng>>29)return;
 memset(ix_local,0,sizeof ix_local);ix_id=0;ix_on=1;ix_edge=ix_start=ix_now();}
static void ix_exit(void){
 if(!ix_depth)abort();if(--ix_depth)return;if(!ix_on)return;
 ix_stage(0);ix_on=0;ix_wall+=ix_edge-ix_start;++ix_taken;
 for(unsigned i=0;i<10;i++)ix_ns[i]+=ix_local[i];}
void ix_flip(unsigned f){
 if(ix_on){ix_on=0;++ix_cross;}
 if(f==30||f==120){uint64_t freq;__asm__("mrs %0,cntfrq_el0":"=r"(freq));uint64_t sum=0;
 fprintf(stderr,"[INDEX_LEDGER] %u %llu %u %u %u %u %llu",f,(unsigned long long)freq,ix_calls,ix_taken,ix_nested,ix_cross,(unsigned long long)ix_wall);
 for(unsigned i=0;i<10;i++){sum+=ix_ns[i];fprintf(stderr," %llu",(unsigned long long)ix_ns[i]);}
 uint64_t v=0;for(unsigned i=0;i<1024;i++){uint64_t t=ix_now();v+=ix_now()-t;}
 fprintf(stderr," cal1024=%llu\n",(unsigned long long)v);if(sum!=ix_wall)abort();}
 if(f==0||f==30){ix_calls=ix_taken=ix_cross=ix_nested=0;ix_ticks=ix_wall=0;memset(ix_ns,0,sizeof ix_ns);}
 ix_f=f<120?f+1:0;
}
'''+k)
s=edit(s,'    track_draw_call(fn, 1);','    track_draw_call(fn, 1);if(fn==D3DF_D3DDevice_DrawIndexedVertices)ix_enter();')
s=edit(s,'    if (took) track_draw_call(fn, 0);','    if(fn==D3DF_D3DDevice_DrawIndexedVertices){if(took)ix_exit();else ix_stage(9);}\n    if (took) track_draw_call(fn, 0);')
s=edit(s,'    d3d_hle_after(fn, regs);','    d3d_hle_after(fn, regs);if(fn==D3DF_D3DDevice_DrawIndexedVertices)ix_exit();')
if single:
 a=s.index('static unsigned ix_f');b=s.index('int d3d_hook(int fn)',a)
 keep=s[s.index('static inline uint64_t ix_now',a):s.index('void ix_stage',a)]
 s=s[:a]+keep+r"""
static unsigned ix_f,ix_depth,ix_rng=7351,ix_id,ix_pick,ix_run,ix_calls,ix_seen[12],ix_bad;
static uint64_t ix_t,ix_cost[12];unsigned ix_on;
void ix_stage(unsigned k){
 if(!ix_on)return;
 if(ix_id==ix_pick && ix_run){ix_cost[ix_pick]+=ix_now()-ix_t;ix_run=0;}
 ix_id=k;
 if(k==ix_pick){ix_t=ix_now();ix_run=1;}
}
static void ix_enter(void){
 if(ix_depth++){if(ix_on)++ix_bad;ix_on=0;return;}if(!ix_f)return;
 ++ix_calls;ix_rng=1664525u*ix_rng+1013904223u;ix_pick=((uint64_t)ix_rng*12)>>32;
 ++ix_seen[ix_pick];ix_on=1;ix_run=0;ix_id=99;
 if(ix_pick==10){ix_t=ix_now();}else if(ix_pick==11){uint64_t a=ix_now();ix_cost[11]+=ix_now()-a;}else ix_stage(0);
}
static void ix_exit(void){
 if(!ix_depth)abort();if(--ix_depth || !ix_on)return;
 if(ix_pick==10)ix_cost[10]+=ix_now()-ix_t;else ix_stage(99);ix_on=0;}
void ix_flip(unsigned f){
 if(ix_on){ix_on=0;++ix_bad;}
 if(f==30||f==120){uint64_t hz;__asm__("mrs %0,cntfrq_el0":"=r"(hz));
 fprintf(stderr,"[IX_SINGLE] %u %llu %u %u",f,(unsigned long long)hz,ix_calls,ix_bad);
 for(unsigned i=0;i<12;i++){fprintf(stderr," %u:%llu",ix_seen[i],(unsigned long long)ix_cost[i]);}fputc(10,stderr);}
 if(!f||f==30){memset(ix_seen,0,sizeof ix_seen);memset(ix_cost,0,sizeof ix_cost);ix_bad=ix_calls=0;}ix_f=f<120?f+1:0;
}
"""+s[b:]
p.link[p.link.index(str(p.core/'exact-hooks.c.o'))]=p.compile('direct/hooks.c','#include <stdio.h>\n'+s,['-include',str(RUNTIME/'switch_guest_regs.h')])
pre='extern "C"{extern unsigned ix_on;void ix_stage(unsigned);}\n#define IX(n) do{if(ix_on)ix_stage(n);}while(0)\n'
s=(ROOT/'src/d3d/hle.cpp').read_text()
s=edit(s,'    SyncDeferred();','    IX(1);SyncDeferred();')
s=edit(s,'    if (g_backend) g_backend->Draw(g_state, prim, start, count, indices);','    IX(2);if (g_backend) g_backend->Draw(g_state, prim, start, count, indices);IX(0);')
p.add('hle.cpp',pre+s)
s=(ROOT/'src/d3d/gpu/threaded.cpp').read_text()
s=edit(s,'        SendState(s, start + count);','        IX(3);SendState(s, start + count);IX(7);')
s=edit(s,'        FlushHeaders();\n        SendPeek(s);','        FlushHeaders();IX(4);\n        SendPeek(s);IX(5);')
s=edit(s,'        const size_t constant_offset','        IX(6);const size_t constant_offset')
k='        cur_->cmds.push_back(c);\n        if (!thread_ || cur_->cmds.size() >= kBatchCommands) Submit();';assert s.count(k)==1;s=s.replace(k,'        IX(8);'+k)
p.add('threaded.cpp',pre+s)
s=(RUNTIME/'scene/bridge.c').read_text()
for k,f in [('            ngb_direct_reset_stats();','0'),('    ++scene_flips;','scene_flips')]:
 s=edit(s,k,k+f' extern void ix_flip(unsigned);ix_flip({f});')
p.add('scene/bridge.c',s);p.link.insert(1,'-Wl,--strip-debug');p.finish()
