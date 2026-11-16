"""Compare the entire generated 77270 allocator, including failure/null paths."""
from pathlib import Path
import subprocess,runpy,tempfile
p=Path(__file__).resolve().parent
s=Path('build/switch-runtime/gen/recomp_0005.c').read_text()
def body(s):
 a=s.index('void sub_00077270(void)\n{');return s[a:s.index('\n}',a)+2]
h=r'''
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#define NGB_VM_BEGIN (1u<<24)
#define NGB_RAM_BYTES NGB_VM_BEGIN
static unsigned char ngb_fast_ram[NGB_RAM_BYTES],before[256],expected[256];
static uint16_t ngb_fast_page_bytes[4096];
static struct regs {uint32_t a,c,d,di,si,sp;} regs;
#define eax regs.a
#define ecx regs.c
#define edx regs.d
#define edi regs.di
#define esi regs.si
#define esp regs.sp
static int g_df;
typedef uint32_t W __attribute__((aligned(1),may_alias));
#define MEM32(a) (*(volatile W*)(ngb_fast_ram+((a)&0xffffffu)))
#define RECOMP_ENTRY(x) ((void)0)
#define CMP_B(a,b) ((a)<(b))
#define CMP_EQ(a,b) ((a)==(b))
#define PUSH32(s,v) do{uint32_t tmp=(v);(s)-=4;MEM32(s)=tmp;}while(0)
#define POP32(s,v) do{v=MEM32(s);(s)+=4;}while(0)
static unsigned polls,calls,addrs[2];
static void ngb_guest_block_poll(void){polls++;}
static void *ngb_guest_pointer(unsigned a,unsigned n){if(calls>=2||n!=64)abort();addrs[calls++]=a;return ngb_fast_ram+(a&0xffffffu);}
'''
h+=body(s).replace('sub_00077270','ref')+'\n'+body(runpy.run_path(str(p/'slot-copy.py'))['transform'](s)).replace('sub_00077270','alt')
h+=r'''
int main(void){
 unsigned trials=0;
 const unsigned slots[]={0,1,2047,2048,0xffffffff};
 for(unsigned i=0;i<sizeof ngb_fast_ram;i++)ngb_fast_ram[i]=(i*31u+(i>>5)*23u)&255;
 for(unsigned m=0;m<5;m++)for(unsigned mode=0;mode<8;mode++)for(int j=-65;j<70;j++){
 unsigned slot=slots[m],dst=0x957100+64*(slot&2047),src=j==-65?0:j<0?0x6000+j:dst+j-32;
 if(src&&(mode&1))src|=0x80000000u;
 g_df=mode>>2;ngb_fast_page_bytes[(src&0xffffffu)>>12]=(mode&2)?0:4096;
 struct regs init={src,0x23232323,7,0xfa55,0xab67,0xb000},want;
 unsigned count,stack[2],original[2]={MEM32(0xaff8),MEM32(0xaffc)};
 memcpy(before,ngb_fast_ram+dst-96,256);
 for(int side=0;side<2;side++){
  regs=init;polls=calls=0;MEM32(0xaff8)=original[0];MEM32(0xaffc)=original[1];
  memcpy(ngb_fast_ram+dst-96,before,256);MEM32(0x977108)=slot;
  if(side)alt();else ref();
  if(polls!=1||(calls&&(calls!=2||addrs[0]!=dst||addrs[1]!=src)))abort();
  if(!side){want=regs;count=MEM32(0x977108);stack[0]=MEM32(0xaff8);stack[1]=MEM32(0xaffc);memcpy(expected,ngb_fast_ram+dst-96,256);}
  else if(memcmp(&regs,&want,sizeof regs)||MEM32(0x977108)!=count||MEM32(0xaff8)!=stack[0]||MEM32(0xaffc)!=stack[1]||memcmp(expected,ngb_fast_ram+dst-96,256))abort();
 }trials++;
 }printf("slot-copy verified %u allocator cases\n",trials);
}
'''
with tempfile.TemporaryDirectory() as td:
 f=Path(td)/'check.c';f.write_text(h)
 subprocess.run(['cc','-O2',str(f),'-o',td+'/check'],check=True);subprocess.run([td+'/check'],check=True)
