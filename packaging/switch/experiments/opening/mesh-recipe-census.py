"""Observe per-part, per-occurrence draw ingredients vs exactly the preceding opening frame."""
from pathlib import Path
import sys,os,runpy
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'perf'))
from native_probe import *
p=NativeProbe('opening-mesh-recipe-census')
def once(s,old,new):
 assert s.count(old)==1,old
 return s.replace(old,new)
s=(RUNTIME/'direct/hooks.c').read_text()
k='void ngb_direct_mesh_scope(int enter)\n{'
s=once(s,k,'''#include <time.h>
static unsigned recipe_rng=971;
int recipe_timing=-1;
unsigned long long recipe_start;
unsigned long long recipe_now(void){struct timespec t;if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t))abort();return 1000000000ull*t.tv_sec+t.tv_nsec;}
unsigned recipe_calls[9],recipe_frame,recipe_key,recipe_pc,recipe_in;
'''+k+'''
 if(recipe_frame && enter){if(recipe_in)abort();for(unsigned i=0;i<9;i++)recipe_calls[i]=0;recipe_in=1;recipe_key=MEM32(esp+4);recipe_pc=MEM32(esp);if(recipe_timing<0)recipe_timing=getenv("NGB_RECIPE_CLOCK")!=0; recipe_start=0;if(recipe_timing){recipe_rng=1664525u*recipe_rng+1013904223u;if((recipe_rng>>29)==0)recipe_start=recipe_now();}}
 if(!enter)recipe_in=0;
''')
p.link[p.link.index(str(p.core/'exact-hooks.c.o'))]=p.compile('direct/hooks.c',s,['-include',str(RUNTIME/'switch_guest_regs.h')])
s=(ROOT/'src/d3d/gpu/threaded.cpp').read_text()
s='#include <map>\n#include <tuple>\n#include <vector>\n'+s
k='    bool Init(uint32_t width'
s=once(s,k,Path(__file__).with_name('mesh-recipe-census.inc').read_text()+'\n'+k)
s=once(s,'        const size_t before = cur_->cmds.size();','        if(recipe_in && recipe_frame){pre_elapsed_=recipe_start?recipe_now()-recipe_start:0;RecipeObserve(s,prim,start,count,indices);}\n        const size_t before = cur_->cmds.size();')
s=once(s,'#include <map>','extern "C" { extern unsigned long long recipe_start,recipe_now(void);extern unsigned recipe_calls[9],recipe_in,recipe_key,recipe_pc,recipe_frame; }\n#include <map>')
if os.getenv('NGB_RECIPE_RANK'):
    s=once(s,'#include <map>','#include <map>\n#include <array>\n#include <cstdio>\n'+Path(__file__).with_name('recipe-pre-rank.inc').read_text())
    s=once(s,'auto &v=pre_draw_[cost_group];','recipe_add(recipe_pc, (s.vs_handle&1)!=0, it==recipes_prev_.end()?64:(bits&22),cost_group,pre_elapsed_);auto &v=pre_draw_[cost_group];')
p.add('gpu/threaded.cpp',s)
s=(RUNTIME/'scene/bridge.c').read_text()
for k,val in [('            ngb_direct_reset_stats();','1'),('    ++scene_flips;','scene_flips<120?scene_flips+1:0')]:
 s=once(s,k,k+' {extern unsigned recipe_frame;recipe_frame='+val+';}')
if os.getenv('NGB_RECIPE_RANK'):
    s=once(s,'++scene_flips;', '++scene_flips; if(scene_flips==120){extern void recipe_rank_report(void);recipe_rank_report();}')
p.add('scene/bridge.c',s)
if os.getenv('NGB_RECIPE_SETTERS'):runpy.run_path(str(Path(__file__).with_name('recipe-setter-probe.py')))['install'](p,REGS)
p.driver('')
p.link.insert(1,'-Wl,--strip-debug');p.finish()
