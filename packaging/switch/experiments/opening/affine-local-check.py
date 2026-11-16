"""Differentially run the two generated routine bodies; check bytes, register results and slow reads."""
from pathlib import Path
import tempfile,subprocess,runpy
p=Path(__file__).parent; gen=Path('build/switch-runtime/gen')
s=(gen/'recomp_0000.c').read_text();a=s.index('void sub_00011110(void)\n{');s=s[a:s.index('\n}',a)+2]
t=runpy.run_path(str(p/'affine-local.py'))['transform'](s,0)
h=(gen/'recomp_types.h').read_text()
src=r"""
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
typedef union {float f[4];uint32_t u[4];uint64_t q[2];double d[2];} RecompXmm;
static unsigned char ram[24576],initial[24576],expected[24576],*ngb_fast_ram=ram;
static uint16_t ngb_fast_page_bytes[1<<20];static uint32_t eax,ecx,esp,trace[32],n;
static RecompXmm xmm1,xmm2,xmm3;
static void *addr(uint32_t v,unsigned z){if((v&4095)+z>ngb_fast_page_bytes[v>>12])trace[n++]=v^z;return ram+(v&0x7fffffff);}
#define RECOMP_ENTRY(x) ((void)0)
#define READ(T,v) __extension__ ({T x;memcpy(&x,addr(v,sizeof x),sizeof x);x;})
#define MEM32(v) READ(uint32_t,v)
#define MEMF(v) READ(float,v)
#define XMM_MEM(v) READ(RecompXmm,v)
#define XMM_STORE(v,x) memcpy(addr(v,16),&(x),16)
"""
for name in ('XMM_ZERO','XMM_SCALAR','XMM_SHUFFLE'):
 a=h.index('static inline RecompXmm '+name+'(');src+=h[a:h.index('\n}',a)+2]+'\n'
src+=h[h.index('#define RECOMP_XMM_LANEWISE'):h.index('RECOMP_XMM_LANEWISE(XMM_SUB')]+ 'RECOMP_XMM_LANEWISE(XMM_MUL, a.f[i] * b.f[i])\n'
src+=s.replace('sub_00011110','ref')+'\n'+t.replace('sub_00011110','alt')
src+=r"""
int main(void){
 for(unsigned j=0;j<1024;j++){
  unsigned pt=(j&1?8187:512)+(j%4),mat=(j&2?12280:1024)+(j%7),sp=(j&4?4090:128);
  unsigned dest=(j&8?pt+1:j&16?mat+1:20000);
  for(unsigned i=0;i<sizeof ram;i++)initial[i]=(i*37+j*13)^(i>>5);
  uint32_t av[3]={dest,pt|((j&32)?0x80000000:0),mat|((j&64)?0x80000000:0)};
  memcpy(initial+sp+4,av,12);for(unsigned k=0;k<6;k++)ngb_fast_page_bytes[k]=ngb_fast_page_bytes[0x80000+k]=(j&128&&k==0?0:4096);
  RecompXmm r[3];unsigned st[35];
  for(unsigned arm=0;arm<2;arm++){
   n=0;memcpy(ram,initial,sizeof ram);esp=sp;eax=ecx=0;xmm1=xmm2=xmm3=XMM_ZERO();
   if(arm)alt();else ref();
   RecompXmm v[]={xmm1,xmm2,xmm3};if(!arm){memcpy(expected,ram,sizeof ram);memcpy(r,v,sizeof r);st[0]=n;st[1]=eax;st[2]=ecx;memcpy(st+3,trace,n*4);}
   else if(esp!=sp+4||eax!=st[1]||ecx!=st[2]||n!=st[0]||memcmp(st+3,trace,n*4)||memcmp(v,r,sizeof r)||memcmp(ram,expected,sizeof ram))abort();
  }
 }puts("1024 matched");}
"""
with tempfile.TemporaryDirectory() as tmp:
 f=Path(tmp)/'check.c';f.write_text(src);exe=f.with_suffix('')
 subprocess.run(['cc','-O2','-ffp-contract=off','-fno-fast-math',str(f),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
