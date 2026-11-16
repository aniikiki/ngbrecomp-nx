"""Compare the actual generated loop before/after the change with a mock guest poll."""
from pathlib import Path
import runpy, subprocess, tempfile
d=Path(__file__).resolve().parent
s=Path('build/switch-runtime/gen/recomp_0028.c').read_text()
new=runpy.run_path(str(d/'light-clear.py'))['transform'](s)
def body(s):
    a=s.index('loc_00308170:');return s[a:s.index('loc_00308181:',a)]
h="""
#include <string.h>
#include <stdint.h>
#include <stdio.h>
#define BASE 0x9AC118u
static unsigned char ram[0x9ad000] __attribute__((aligned(16)));
static unsigned char *ngb_fast_ram;
static uint64_t ngb_guest_polls;
static uint32_t edi,_fa,_fb,ngb_poll_mask,ngb_pending_dpcs,calls,redirect;
static int32_t _fas,_fbs;
#define CMP_L(x,y) ((x)<(y))
#define MEM32(a) (*(volatile uint32_t*)(ram+(a)))
static void ngb_guest_block_poll(void){
    ++ngb_guest_polls;
    if(!(ngb_guest_polls & ngb_poll_mask)||ngb_pending_dpcs){
        ++calls; ngb_pending_dpcs=0;
        if(redirect && calls==1)edi=BASE+7*124;
    }
}
"""
main="""
int main(void){
 unsigned char expect[1152]; unsigned trials=0;
 for(unsigned i=0;i<10;i++)for(unsigned mask=0;mask<32;mask++)
 for(unsigned ticket=0;ticket<32;ticket++)for(unsigned bits=0;bits<16;bits++){
 uint64_t saved[7];
 for(unsigned alt=0;alt<2;alt++){
 ngb_guest_polls=(bits&8?UINT64_MAX-31:0)+ticket;
 ngb_poll_mask=mask; ngb_pending_dpcs=bits&1;redirect=bits&2;
 ngb_fast_ram=bits&4?ram:0;calls=0;
 edi=i<8?BASE+i*124:i==8?BASE-4:BASE+4;
 memset(ram+BASE-16,0xab,sizeof expect);
 (alt?candidate:original)();
 uint64_t got[]={edi,_fa,_fb,(uint32_t)_fas,(uint32_t)_fbs,ngb_guest_polls,((uint64_t)calls<<32)|ngb_pending_dpcs};
 if(!alt){memcpy(saved,got,sizeof got);memcpy(expect,ram+BASE-16,sizeof expect);}
 else if(memcmp(saved,got,sizeof got)||memcmp(expect,ram+BASE-16,sizeof expect))return 1;
 }trials++;
 }printf("%u loop comparisons passed\\n",trials);
}
"""
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp);src=p/'test.c'
 src.write_text(h+''.join('static void '+name+'(void){'+body(text)+'loc_00308181: return;}\n' for name,text in [('original',s),('candidate',new)])+main)
 subprocess.run(['cc','-O2',src,'-o',p/'test'],check=True)
 subprocess.run([p/'test'],check=True)
