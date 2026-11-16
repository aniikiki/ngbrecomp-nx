"""Execute both versions of the exact lifted function against identical synthetic RAM."""
import runpy,tempfile,subprocess
from pathlib import Path
p=Path(__file__).resolve().parent
s=Path('build/switch-runtime/gen/recomp_0033.c').read_text()
candidate=runpy.run_path(str(p/'stack-inner-span.py'))['transform'](s,33)
def get(s):
 a=s.index('void sub_003433F0(void)\n{');return s[a:s.index('\n}',a)+2]
code=r'''
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
static unsigned char ram[1<<22], original[1<<22], expected[1<<22];
static unsigned reg_ends[1<<20],rs[9],polls;
#define ngb_fast_ram ram
#define eax rs[0]
#define ebx rs[1]
#define ecx rs[2]
#define edx rs[3]
#define esi rs[4]
#define edi rs[5]
#define esp rs[6]
#define g_ebp rs[7]
#define g_seh_ebp rs[8]
#define RECOMP_ENTRY(x) ((void)0)
#define ngb_guest_block_poll() (++polls)
static unsigned char* ptr(uint32_t x){x&=0x7fffffff;if(x>sizeof(ram)-4)abort();return ram+x;}
#define MEM32(x) (*(volatile uint32_t*)ptr(x))
#define MEM16(x) (*(volatile uint16_t*)ptr(x))
#define SMEM16(x) (*(volatile int16_t*)ptr(x))
#define SMEM8(x) (*(volatile int8_t*)ptr(x))
#define PUSH32(sp,v) do{uint32_t t=(v);sp-=4;MEM32(sp)=t;}while(0)
#define POP32(sp,v) do{v=MEM32(sp);sp+=4;}while(0)
#define SET_HI8(r,v) ((r)=((r)&0xffff00ff)|((uint32_t)(uint8_t)(v)<<8))
#define SET_LO16(r,v) ((r)=((r)&0xffff0000)|(uint16_t)(v))
#define LO8(v) ((uint8_t)(v))
#define HI8(v) ((uint8_t)((v)>>8))
#define LO16(v) ((uint16_t)(v))
#define SX16(v) ((int16_t)(v))
#define ZX8(v) ((uint8_t)(v))
#define CMP_LE(a,b) ((int32_t)(a)<=(int32_t)(b))
#define CMP_L(a,b) ((int32_t)(a)<(int32_t)(b))
#define CMP_GE(a,b) ((int32_t)(a)>=(int32_t)(b))
#define CMP_G(a,b) ((int32_t)(a)>(int32_t)(b))
'''
code+=get(s).replace('sub_003433F0','ref')+'\n'+get(candidate).replace('sub_003433F0','trial')
code+=r'''
static uint32_t rnd=1337;static unsigned next(void){return rnd=rnd*1664525+1013904223;}
int main(void){
 unsigned runs=0,active=0;for(unsigned i=0;i<sizeof ram;i++)original[i]=next()>>24;
 for(unsigned k=0;k<160;k++){
 memcpy(ram,original,sizeof ram);for(unsigned i=0;i<9;i++)rs[i]=next();
 esp=0x10000+(k%4==0?4*(k%24):0x400)+(k%2?0x80000000u:0u);
 for(unsigned j=(esp-64)>>12;j<=((esp+128)>>12);j++)reg_ends[j]=k%5?(j<<12)+4093u:0;
 unsigned args[]={0x21000,2*(k%6),0x30000,0x31000,0x32000,0x33000,0x1400,0xf800,0x34000,3,7};
 for(unsigned j=0;j<11;j++)MEM32(esp+4+4*j)=args[j];
 for(unsigned j=0;j<10;j++)ram[0x21000+18*j]=(k%7==0?0x80:0)|(next()&31);
 unsigned regs[9],want[9],pc;memcpy(regs,rs,sizeof rs);
 /* Both runs use the same mapped bytes for modeled paged slow access. */
 unsigned char saved[0x40000];memcpy(saved,ram,sizeof saved);
 polls=0;ref();pc=polls;active+=pc>10;memcpy(want,rs,sizeof rs);memcpy(expected,ram,sizeof ram);
 memcpy(ram,original,sizeof ram);memcpy(ram,saved,sizeof saved);memcpy(rs,regs,sizeof rs);polls=0;trial();
 if(polls!=pc||memcmp(want,rs,sizeof rs)||memcmp(expected,ram,sizeof ram))return 1;
 runs++;
 }printf("full function equivalence %u cases, %u with >10 polls\n",runs,active);return !active;}
'''
with tempfile.TemporaryDirectory() as td:
 f=Path(td)/'check.c';f.write_text(code);binary=f.with_suffix('')
 subprocess.run(['cc','-fno-strict-aliasing','-O2',f,'-o',binary],check=True)
 subprocess.run([binary],check=True)
