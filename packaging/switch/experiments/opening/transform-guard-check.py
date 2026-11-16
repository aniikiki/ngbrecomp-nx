"""Compile the actual before/after helpers and compare admission + XMM bytes."""
from pathlib import Path
import runpy,tempfile,subprocess
p=Path(__file__).resolve().parent
h=(p.parents[1]/'runtime/arm_math.h').read_text()
k='static inline bool ngb_arm_transform'
c='''
#include <arm_neon.h>
#include <stdint.h>
#include <stdbool.h>
#include <math.h>
#include <assert.h>
#include <string.h>
#include <stdio.h>
static unsigned char mem[4096],g_xmm1[16],g_xmm2[16],g_xmm3[16];
static void* ngb_ram_span(uint32_t a,unsigned n){return a<=sizeof(mem)-n?mem+a:NULL;}
'''+h[h.index('static inline bool ngb_arm_finite'):h.index('/* In this range')]
for n,s in enumerate((h,runpy.run_path(str(p/'transform-guard.py'))['header']())):
 c+=s[s.index(k):].replace('ngb_arm_transform',f'fn{n}',1)
c+='''
int main(void){unsigned count=0;uint32_t seed=1;
uint32_t bits[]={0,0x80000000,1,0x7fffff,0x00800000,0x3f800000,0xff7fffff,0x7f800000,0xff800000,0x7fc00001,0x7f800001};
for(unsigned tr=0;tr<2;tr++)for(unsigned i=0;i<19;i++)for(unsigned j=0;j<sizeof(bits)/4;j++)for(unsigned n=0;n<32;n++){
 for(int v=0;v<19;v++){uint32_t a=32+4*v;seed=1664525*seed+1013904223;
 uint32_t x=(seed&0x807fffff)|0x3f000000;if(v==(int)i)x=bits[j];memcpy(mem+a,&x,4);}
 uint32_t src=n==0?4090:32,mat=n==1?4080:44;
 unsigned char out[48];int valid=0;
 for(int pass=0;pass<2;pass++){memset(g_xmm1,11,16);memset(g_xmm2,22,16);memset(g_xmm3,33,16);
 int ok=pass?fn1(src,mat,tr):fn0(src,mat,tr);
 if(!pass){valid=ok;memcpy(out,g_xmm1,16);memcpy(out+16,g_xmm2,16);memcpy(out+32,g_xmm3,16);}
 else assert(ok==valid&&!memcmp(out,g_xmm1,16)&&!memcmp(out+16,g_xmm2,16)&&!memcmp(out+32,g_xmm3,16));}count++;}
printf("%u matching original/candidate results and XMM outputs\\n",count);}
'''
with tempfile.TemporaryDirectory() as d:
 f=Path(d)/'check.c';exe=f.with_suffix('');f.write_text(c)
 subprocess.run(['cc','-O2','-ffp-contract=off',str(f),'-o',str(exe)],check=True);subprocess.run([exe],check=True)
