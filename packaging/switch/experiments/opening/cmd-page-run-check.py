"""Differential test of the actual three generated backedge/head blocks."""
from pathlib import Path
import runpy, subprocess, tempfile
here=Path(__file__).resolve().parent
src=Path('build/switch-runtime/gen/recomp_0010.c').read_text()
new=runpy.run_path(str(here/'cmd-page-run.py'))['transform'](src)[0]
pre=r'''
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#define CMP_NE(a,b) ((a)!=(b))
#define CMP_A(a,b) ((a)>(b))
#define MEM32(v) load(v)
static unsigned char ram[16384];static unsigned char *ngb_fast_ram=ram;
static unsigned ngb_fast_page_bytes[4],ecx,edx,_fa,_fb;
static int _fas,_fbs;
static unsigned long long ngb_guest_polls;static unsigned ngb_poll_mask,ngb_pending_dpcs,calls,special,mode;
static unsigned load(unsigned v){unsigned val; if(v>=sizeof(ram)-3)abort();memcpy(&val,ram+v,4);special+=(v%4096+4>ngb_fast_page_bytes[v/4096]);return val;}
static void ngb_poll_due(unsigned long long t){
 ++calls;ngb_pending_dpcs=0;
 if(calls==1 && mode){if(mode&1)ecx+=4;if(mode&2)ngb_fast_page_bytes[ecx/4096]=0;
 if(mode&4){unsigned k=0x90000005u;memcpy(ram+ecx,&k,4);}}
}
static void ngb_guest_block_poll(void){unsigned long long t=++ngb_guest_polls;if(!(t&ngb_poll_mask)||ngb_pending_dpcs)ngb_poll_due(t);}
'''
def gen(s,ix,name,head,back,dispatch,after):
 def block(x,y):return s[s.index('loc_'+x+': ;'):s.index('loc_'+y+': ;')]
 return f'static unsigned {name}{ix}(void){{goto loc_{back};\n'+block(head,dispatch)+f'loc_{dispatch}: ;return 1;\n'+block(back,after)+f'loc_{after}: ;return 2;}}\n'
cases=[('00149CF0','00149F19','00149D04','00149F25'),('00149F41','0014A15B','00149F55','0014A167'),('0014A183','0014A386','0014A197','0014A392')]
code=pre+''.join(gen(s,i,n,*c) for i,c in enumerate(cases) for n,s in [('orig',src),('fast',new)])
code+=r'''
static unsigned (*f[3][2])(void)={{orig0,fast0},{orig1,fast1},{orig2,fast2}};
int main(void){unsigned count=0;
for(unsigned i=0;i<3;i++)for(unsigned test=0;test<16384;test++){
 unsigned result[2][14];
 for(unsigned v=0;v<2;v++){
 memset(ram,0,sizeof ram);ecx=4076+(test%16);edx=1234;_fa=_fb=_fas=_fbs=0;
 unsigned at=ecx+4*((test>>2)%63);unsigned end=test&128?0x90000001+4*i+(test%4):0x9000000D;
 memcpy(ram+at,&end,4);end=0x9000000D;memcpy(ram+at+12,&end,4);
 ngb_fast_page_bytes[0]=test&8?4096:4092;ngb_fast_page_bytes[1]=test&16?4096:0;
 calls=special=0;ngb_guest_polls=test%13;ngb_poll_mask=(1u<<(test%6))-1;ngb_pending_dpcs=(test>>6)&1;mode=(test>>9)%8;
 unsigned r=f[i][v]();unsigned out[]={r,ecx,edx,_fa,_fb,(unsigned)_fas,(unsigned)_fbs,(unsigned)ngb_guest_polls,calls,special,ngb_pending_dpcs,ngb_fast_page_bytes[0],ngb_fast_page_bytes[1],load(ecx)};
 memcpy(result[v],out,sizeof out);}
 if(memcmp(result[0],result[1],sizeof result[0])){fprintf(stderr,"mismatch %u %u\n",i,test);return 1;}count++;}
 printf("%u backedge cases matched\n",count);}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t)/'check.c';p.write_text(code);out=p.with_suffix('')
 subprocess.run(['cc','-O2',str(p),'-o',str(out)],check=True);subprocess.run([out],check=True)
