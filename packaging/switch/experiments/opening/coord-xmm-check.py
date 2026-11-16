"""Test the exact transformed fragment against its source, including overlaps and fallback."""
from pathlib import Path
import subprocess,tempfile,runpy
p=Path(__file__).resolve().parent
s=Path('build/switch-runtime/gen/recomp_0028.c').read_text()
v=runpy.run_path(str(p/'coord-xmm.py'))['transform'](s,28)
def body(t):
 i=t.index('void sub_003059A0(void)\n{');i=t.index('/* movss */',t.index('MEMF(edx + 0xC) =',i))+len('/* movss */')
 return t[i:t.index('    POP32(',i)]
c=r'''
#include <stdint.h>
#include <string.h>
#include <assert.h>
#define NGB_RAM_BYTES (64u<<20)
typedef union {float f[4];uint32_t u[4];} RecompXmm;
static RecompXmm xmm0;
static uint8_t backing[0x9501d0],*ngb_fast_ram;
static uint16_t ngb_fast_page_bytes[1<<20];
static uint32_t edx;
#define XMM_SCALAR(v) ((RecompXmm){.f={v,0,0,0}})
#define MEMF(a) (*(float*)(backing+(a)))
'''
c+='static void ref(void){'+body(s)+'}\nstatic void opt(void){'+body(v)+'}\n'
c+=r'''
int main(void){
 uint32_t offsets[]={0x9501a8,0x9501ac,0x9501b0,0x9501b4,0x9501b8,0x94fff8,0x94fffc,0x950000};
 uint8_t init[0x240],expected[sizeof(init)];
 for(unsigned k=0;k<sizeof(init);k++)init[k]=(uint8_t)(k*37+13);
 for(unsigned n=0;n<8;n++)for(int mapped=0;mapped<=1;mapped++)for(int live=0;live<=1;live++){
 edx=offsets[n];ngb_fast_ram=live?backing:0;ngb_fast_page_bytes[edx>>12]=mapped?4096:0;
 memcpy(backing+0x94ff90,init,sizeof(init)); ref();RecompXmm x=xmm0;
 memcpy(expected,backing+0x94ff90,sizeof(init));memcpy(backing+0x94ff90,init,sizeof(init));memset(&xmm0,0x55,sizeof(xmm0));opt();
 assert(!memcmp(&x,&xmm0,sizeof(x))&&!memcmp(expected,backing+0x94ff90,sizeof(init)));
 }}
'''
with tempfile.TemporaryDirectory() as t:
 f=Path(t)/'check.c';f.write_text(c);out=f.with_suffix('')
 subprocess.run(['cc','-O2','-fno-strict-aliasing',str(f),'-o',out],check=True);subprocess.run([out],check=True)
print('32 reference/candidate comparisons passed')
