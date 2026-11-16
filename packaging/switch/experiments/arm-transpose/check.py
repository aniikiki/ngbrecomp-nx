"""Execute the actual specialized and original function bodies on ARM; compare
all RAM, output registers and all eight physical x87 slots for every call."""
from pathlib import Path
import subprocess as sp,re
d=Path('/work/build/switch-runtime/core-perf/transpose')
s=re.search(r'void sub_0037A480\(void\)\n\{.*?^\}',(d/'recomp_0039.c').read_text(),re.M|re.S)[0]
src=r'''#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <arm_neon.h>
unsigned eax,ecx,edx,esp,g_fp_top,trial_variant,transpose_hits;double g_fp_stack[8];
static union {uint32_t w[256];float f[256];} ram,original,expected;
#define MEM32(a) ram.w[(a)/4]
#define MEMF(a) ram.f[(a)/4]
#define CMP_EQ(a,b) ((a)==(b))
#define RECOMP_ENTRY(a) ((void)0)
static void*ngb_ram_span(unsigned a,unsigned b){return a+b<=sizeof(ram)?(char*)&ram+a:0;}
'''+s+r'''
int main(void){
unsigned seed=17;for(unsigned i=0;i<40000;i++){
 for(unsigned j=0;j<256;j++){seed=seed*1664525+1013904223;original.w[j]=i%3?((seed&0x807fffff)|0x3f000000):seed;}
 unsigned in=128, out=i%4==0?128:i%4==1?160:i%4==2?112:512;
 unsigned regs[5];double fp[8];
 for(int v=0;v<2;v++){ram=original;eax=11;ecx=17;edx=41;esp=16;g_fp_top=i%8;
 for(unsigned j=0;j<8;j++)g_fp_stack[j]=i+j+0.125;
 MEM32(esp+4)=out;MEM32(esp+8)=in;trial_variant=v;sub_0037A480();
 unsigned r[]={eax,ecx,edx,esp,g_fp_top};
 if(!v){expected=ram;memcpy(regs,r,sizeof r);memcpy(fp,g_fp_stack,sizeof fp);}
 else if(memcmp(&expected,&ram,sizeof ram)||memcmp(regs,r,sizeof r)||memcmp(fp,g_fp_stack,sizeof fp)){printf("mismatch %u\n",i);return 1;}
 }}printf("40000 original/specialized calls match, %u entered NEON\n",transpose_hits);return !transpose_hits;}
'''
f=d/'check.c';f.write_text(src);sp.run(['cc','-O2','-fno-strict-aliasing',f,'-o',d/'check'],check=True);sp.run([d/'check'],check=True)
