"""How many HLE Draws actually arise inside a single 30BCA0 submitter invocation?"""
from pathlib import Path
import sys
h=Path(__file__).resolve().parent;sys.path.insert(0,str(h.parents[1]/'perf'))
from native_probe import *
p=NativeProbe('opening-mesh-fanout');p.driver('')
s=(RUNTIME/'direct/hooks.c').read_text()
k='void ngb_direct_mesh_scope(int enter)\n{';assert s.count(k)==1
s=s.replace(k,r'''
static unsigned mf_active,mf_f,mf_depth,mf_start[32],mf_work[32],mf_bins[8],mf_calls,mf_all,mf_out,mf_cross,mf_max;
void mf_draw(void){if(!mf_active)return;++mf_all;if(mf_depth)++mf_work[mf_depth-1];else ++mf_out;}
void mf_flip(unsigned f){
 if(f==30||f==120){fprintf(stderr,"[FANOUT] %u calls=%u draws=%u outside=%u cross=%u max=%u hist=",f,mf_calls,mf_all,mf_out,mf_cross,mf_max);
 for(unsigned i=0;i<8;++i){fprintf(stderr," %u",mf_bins[i]);}fprintf(stderr,"\n");}
 if(f==0||f==30){memset(mf_bins,0,sizeof mf_bins);mf_calls=mf_all=mf_out=mf_cross=mf_max=0;}
 mf_active=f<120;mf_f=f+1;
}
'''+k+r'''
 if(enter){if(mf_depth==32)abort();mf_start[mf_depth]=mf_f;mf_work[mf_depth++]=0;}
 else if(mf_depth){--mf_depth;unsigned n=mf_work[mf_depth];
 if(mf_active){if(mf_start[mf_depth]!=mf_f)++mf_cross;else{++mf_bins[n<7?n:7];++mf_calls;if(n>mf_max)mf_max=n;}}}
''')
p.link[p.link.index(str(p.core/'exact-hooks.c.o'))]=p.compile('direct/hooks.c','#include <stdio.h>\n'+s,['-include',str(RUNTIME/'switch_guest_regs.h')])
s=(ROOT/'src/d3d/hle.cpp').read_text();k='    if (!g_backend) return;\n    bool measure';assert s.count(k)==1
p.add('hle.cpp','extern "C" void mf_draw();\n'+s.replace(k,'    if (!g_backend) return;\n    mf_draw();\n    bool measure'))
s=(RUNTIME/'scene/bridge.c').read_text()
for k,f in [('            ngb_direct_reset_stats();','0'),('    ++scene_flips;','scene_flips')]:
 assert s.count(k)==1;s=s.replace(k,k+f' extern void mf_flip(unsigned);mf_flip({f});')
p.add('scene/bridge.c',s);p.link.insert(1,'-Wl,--strip-debug');p.finish()
