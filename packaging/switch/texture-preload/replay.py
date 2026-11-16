"""Exercise the title device and the same texture hooks as the NRO on a scratch HDD."""
from pathlib import Path
import runpy,sys
p=Path(__file__).resolve().parent
sys.path.insert(0,str(p.parent/'perf'))
from native_probe import *
q=NativeProbe('texture-preload-replay');runpy.run_path(str(p/'index.py'))['emit'](ROOT/'game_files',q.out/'texture_index.inc')
flags=['-DNGB_TEXTURE_PRELOAD','-I'+str(q.out)]
for n in ('files','scanout','identity','opening_movie','pgraph_boot','ohci_boot'):
    old=next(i for i,v in enumerate(q.link) if v.endswith('/'+n+'.c.o'))
    q.link[old]=q.compile(n+'.c',(RUNTIME/(n+'.c')).read_text(),flags)
q.link.insert(1,q.compile('threaded.cpp',(ROOT/'src/d3d/gpu/threaded.cpp').read_text(),flags))
warm=runpy.run_path(str(p.parent/'experiments/opening/hardware-prewarm.py'))
q.link[q.link.index(str(REGS/'backend-host-clip.o'))]=q.compile('vk/backend.cpp',(ROOT/'src/d3d/vk/backend.cpp').read_text().replace('    CacheOpen();','    CacheOpen(); Prewarm();'),flags+['-DNGB_RIGID_CLIP'])
q.link.insert(1,q.compile('hle.cpp',warm['hle']((ROOT/'src/d3d/hle.cpp').read_text()),flags))
# Runtime included in host-driver; use the same movie teardown trigger as Horizon.
s=(REGS/'host-driver.c').read_text()
k='    __real_ngb_kernel_log(message);';assert s.count(k)==1
s=s.replace(k,k+'\n    if(!strncmp(message,"Main menu overlay renderer=",27)){extern void ngb_prepare_title_device(void);ngb_prepare_title_device();}')
# Capture actual completed wide scanouts, not the 4:3 title signature.
k='void __real_ngb_kernel_log'
s=s.replace(k,r"""
#include <stdatomic.h>
static atomic_uint moving_outputs;
void __real_ngb_scanout_direct(const void*);
void __wrap_ngb_scanout_direct(const void* fb){
 static unsigned prev[480],frames;const unsigned* px=fb;unsigned motion=0,color=0;
 for(unsigned i=0;i<480;i++){
  unsigned v=px[(i/24*NGB_SCAN_H/20+8)*NGB_SCAN_W+i%24*NGB_SCAN_W/24+8],dist=0;
  for(unsigned c=0;c<24;c+=8)dist+=abs((int)((v>>c)&255)-(int)((prev[i]>>c)&255));
  motion+=dist>15;color+=(v&255)>48;prev[i]=v;
 }
 if(frames++ && motion>25 && color>80)atomic_fetch_add(&moving_outputs,1);
 __real_ngb_scanout_direct(fb);
}
"""+k,1)
s=s.replace('        CHECK(benchmark_motion);','        fprintf(stderr,"[WIDE] moving=%u\\n",atomic_load(&moving_outputs));CHECK(atomic_load(&moving_outputs)>=8);')
q.link.insert(1,'-Wl,--wrap=ngb_scanout_direct')
bridge=(RUNTIME/'scene/bridge.c').read_text()
k='    intervals[scene_flips-window_flip] = now - previous_flip;'
bridge=bridge.replace(k,k+'\n    if(scene_flips<120)fprintf(stderr,"[TEX_FLIP] %u %llu\\n",scene_flips+1,(unsigned long long)(now-previous_flip));')
q.add('scene/bridge.c',bridge)
q.link[q.link.index(str(q.core/'exact-runtime_test.c.o'))]=q.compile('runtime_test.c',s,['-I'+str(REGS),'-I'+str(RUNTIME),'-include',str(RUNTIME/'switch_guest_regs.h'),'-DNGB_RIGID_CLIP','-DNGB_REGISTER_PACKAGE'])
q.link.insert(1,'-Wl,--strip-debug');q.finish()
