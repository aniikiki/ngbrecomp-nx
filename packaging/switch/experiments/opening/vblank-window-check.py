"""Differential test using the actual two sampling bodies, including callbacks and wrap."""
import runpy, subprocess, tempfile
from pathlib import Path
p=Path(__file__).resolve().parent
src=(p.parents[1]/'runtime/nv2a_boot.c').read_text()
alt=runpy.run_path(str(p/'vblank-window.py'))['transform'](src)
def body(s):
 a=s.index('static void sample_vblank(void)');b=s.index('\n}',a)+2
 return s[a:b]
code='''#include <stdint.h>
#include <stdlib.h>
static uint64_t now,frame,frame_start_ns;static unsigned engines,crtc_status,scanout_start,refresh;
#define ENGINE_CRTC 1
#define NV_PCRTC_INTR_0_VBLANK 4
static uint64_t ngb_elapsed_ns(void){return now;}
static void ngb_scanout_refresh(unsigned a){refresh+=a;}
'''+body(src).replace('sample_vblank','ref')+'\n'+body(alt).replace('sample_vblank','fast')+'''
int main(void){uint64_t fr=0,ff=0,seed=37;unsigned sr=0,sf=0,rr=0,rf=0;
for(unsigned i=0;i<150000;i++){
 seed=seed*6364136223846793005ull+1;
 switch(i%16){case 0:now=seed;break;case 1:now=0;break;case 2:now=UINT64_MAX;break;case 3:case 4:case 5:now=(seed%999)*16666667ull+i%16-4;break;default:now+=seed%300000;break;}
 if(i%43==0){fr=ff=now/16666667u;frame_start_ns=ff*16666667u;}
 if(i%67==0){fr=ff=frame_start_ns=0;}
 engines=seed>>44;scanout_start=(seed>>30)&1;frame=fr;refresh=rr;crtc_status=sr;ref();fr=frame;rr=refresh;sr=crtc_status;
 frame=ff;refresh=rf;crtc_status=sf;fast();ff=frame;rf=refresh;sf=crtc_status;
 if(ff!=fr||sf!=sr||rf!=rr||frame_start_ns!=ff*16666667ull)abort();
 if(i%2==0)sf=sr=0;
}}
'''
with tempfile.TemporaryDirectory() as tmp:
 e=Path(tmp)/'check';subprocess.run(['cc','-O2','-x','c','-o',e,'-'],input=code,text=True,check=True);subprocess.run([e],check=True)
print('150000 VBlank states matched')
