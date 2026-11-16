"""Compare generated row including aliasing, slow paths, and final xmm/edx bits."""
from pathlib import Path
import tempfile,runpy,subprocess
s=Path('build/switch-runtime/gen/recomp_0027.c').read_text()
new=runpy.run_path(str(Path(__file__).with_name('row-three.py')))['transform'](s)
k='loc_00303FB0: ; ngb_guest_block_poll();'
def body(s):
 a=s.index(k)+len(k);b=s.index('    _fb = (uint32_t)(8)',a);return s[a:b]
c='''
#include <stdint.h>
#include <string.h>
#include <assert.h>
#include <stdio.h>
static uint8_t ram[16384] __attribute__((aligned(16))),*ngb_fast_ram=ram;
static unsigned short ngb_fast_page_bytes[1<<20];
struct V{float f[4];};static struct V xmm0,xmm1;
#define XMM_SCALAR(x) ((struct V){{(x),0,0,0}})
#define MEMF(x) (*(volatile float*)(ram+((x)&16383)))
static uint32_t eax,ecx,edx,_fa,_fb;static int32_t _fas,_fbs;
'''
for name,v in [('ref',s),('alt',new)]:c+='static void '+name+'(void){'+body(v)+'}\n'
c+='''
int main(){uint32_t rng=7;static uint8_t saved[16384],expect[16384];struct V x,y;
 for(unsigned i=0;i<12000;i++){
 for(int j=0;j<16384;j+=4){rng=rng*1664525u+1013904223u;memcpy(saved+j,&rng,4);}
 unsigned p=i%5==0?4088:0x180;eax=p+4;ecx=i%3?0x500:p;
 unsigned d=i%4==0?p:i%4==1?ecx+4:0xa00;
 if(i&8){eax|=0x80000000;ecx|=0x80000000;d|=0x80000000;}
 for(unsigned j=0;j<4;j++){ngb_fast_page_bytes[j]=ngb_fast_page_bytes[j+0x80000]=(i&16)?0:4096;}
 memcpy(ram,saved,sizeof ram);edx=d;ref();memcpy(expect,ram,sizeof ram);x=xmm0;y=xmm1;uint32_t out=edx;
 memcpy(ram,saved,sizeof ram);edx=d;alt();assert(out==edx&&!memcmp(expect,ram,sizeof ram)&&!memcmp(&x,&xmm0,sizeof x)&&!memcmp(&y,&xmm1,sizeof y));
 }puts("12000 row comparisons passed");}
'''
with tempfile.TemporaryDirectory() as t:
 f=Path(t)/'r.c';f.write_text(c)
 subprocess.run(['cc','-O2','-ffp-contract=off',f,'-o',f.with_suffix('')],check=True);subprocess.run([f.with_suffix('')],check=True)
