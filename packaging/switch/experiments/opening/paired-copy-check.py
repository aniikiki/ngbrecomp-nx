"""Compare the generated fixed REP MOVSD, including register and fallback side effects."""
from pathlib import Path
import subprocess,tempfile,runpy
p=Path(__file__).resolve().parent
s=Path('build/switch-runtime/gen/recomp_0044.c').read_text()
def part(t):
 a=t.index('ecx = 0x1A;\n    edi = ebx;',t.index('void d3d_orig_003C7490'))
 b=t.index('/* rep movsd */',a)
 return t[a:b]
code=r'''
#include <stdlib.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define NGB_RAM_BYTES 32768
static unsigned char ngb_fast_ram[NGB_RAM_BYTES],orig[NGB_RAM_BYTES];
static unsigned short ngb_fast_page_bytes[8];
static uint32_t ecx,edi,esi,ebx,g_df;
static unsigned calls,addr[2];
static void* ngb_guest_pointer(unsigned va,unsigned n){if(n!=104||calls>=2)abort();addr[calls++]=va;return ngb_fast_ram+(va&32767);}
typedef uint32_t U __attribute__((aligned(1),may_alias));
#define MEM32(a) (*(volatile U*)(ngb_fast_ram+((a)&32767)))
'''
code+='static void ref(void){'+part(s)+'}\nstatic void alt(void){'+part(runpy.run_path(str(p/'paired-copy.py'))['transform'](s))+'}\n'
code+=r'''
int main(void){
 unsigned tests=0;
 for(unsigned mode=0;mode<32;mode++)for(int delta=-105;delta<=105;delta++)for(unsigned i=0;i<8;i++){
 unsigned src=8192-104+i*23,dst=mode&1?src+delta:16384+i*23;
 unsigned sv=src|((mode&2)?0x80000000u:0),dv=dst|((mode&4)?0x80000000u:0);
 g_df=(mode>>3)&1;for(int j=0;j<8;j++)ngb_fast_page_bytes[j]=mode&16?0:4096;
 for(unsigned k=0;k<NGB_RAM_BYTES;k++)ngb_fast_ram[k]=(k*31+(k>>5)*23)&255;
 unsigned char initial[NGB_RAM_BYTES];memcpy(initial,ngb_fast_ram,sizeof initial);
 esi=sv;ebx=dv;calls=0;ref();memcpy(orig,ngb_fast_ram,sizeof orig);unsigned rs=esi,rd=edi,rc=ecx;
 memcpy(ngb_fast_ram,initial,sizeof initial);esi=sv;ebx=dv;calls=0;alt();
 int fast=!g_df && !(mode&22) && (src%4096)+104<=4096 && (dst%4096)+104<=4096 && (src+104<=dst || dst+104<=src);
 if(calls!=(fast||g_df?0:2)||(calls && (addr[0]!=dv||addr[1]!=sv))||esi!=rs||edi!=rd||ecx!=rc||memcmp(orig,ngb_fast_ram,sizeof orig))abort();
 tests++;
 }printf("paired-copy verified %u cases\n",tests);}
'''
with tempfile.TemporaryDirectory() as td:
 f=Path(td)/'check.c';f.write_text(code)
 subprocess.run(['cc','-O2',str(f),'-o',td+'/check'],check=True);subprocess.run([td+'/check'],check=True)
