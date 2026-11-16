"""Keep the existing page check; consume a mapped word directly via the A64 indexed load."""
from pathlib import Path
import re,runpy,sys,subprocess,tempfile
p=Path(__file__).parent
reg=r'e(?:ax|bx|cx|dx|bp|sp|si|di)'
line=re.compile(r'^(    '+reg+r' = )MEM32\(('+reg+r'(?: [+-] (?:0x[0-9A-Fa-f]+|[0-9]+))?)\);',re.M)
helper=r'''
static inline __attribute__((always_inline)) uint32_t ir_word(uint32_t va){
 if(ngb_static_image_span(va,4) && ngb_fast_ram)return *(volatile uint32_t*)(ngb_fast_ram+va);
 if(__builtin_expect(va<reg_ends[va>>12],1)){
  uint32_t v;__asm__ volatile("ldr %w0,[%1,%w2,uxtw]" : "=r"(v) : "r"(ngb_fast_ram),"r"(va&0x7fffffffu) : "memory");return v;
 }
 return *(volatile uint32_t*)ngb_guest_scalar_fallback(va,4);
}
'''
def transform(s,u):
 k='#include "recomp_funcs.h"';assert s.count(k)==1
 s,n=line.subn(r'\1ir_word(\2);',s);assert n
 print(u,n,'direct word reads',flush=True);return s.replace(k,k+helper)
if __name__=='__main__' and '--check' in sys.argv:
 src=r'''
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
static uint8_t ram[8192],fault[4];static uint32_t reg_ends[1<<20],calls,where;
#define ngb_fast_ram ram
#define ngb_static_image_span(a,n) (0)
static uintptr_t ngb_guest_scalar_fallback(uint32_t a,unsigned n){if(n!=4)abort();where=a;++calls;return (uintptr_t)fault;}
'''+helper+r'''
int main(void){
 for(unsigned i=0;i<8192;++i)ram[i]=i*97u+(i>>5);memset(fault,0xb4,4);
 for(unsigned alias=0;alias<2;alias++)for(unsigned enabled=0;enabled<2;enabled++)for(unsigned i=0;i<8192;i++){
  uint32_t va=(alias<<31)+i;reg_ends[va>>12]=enabled?(va&~4095u)+4093u:0;calls=0;where=0;
  unsigned slow=!enabled || (i&4095u)>4092u;uint32_t want;memcpy(&want,slow?fault:ram+i,4);
  if(ir_word(va)!=want||calls!=slow||(slow&&where!=va))abort();
 }puts("32768 exact A64 load/fallback comparisons passed");
}
'''
 with tempfile.TemporaryDirectory() as td:
  f=Path(td)/'check.c';f.write_text(src);subprocess.run(['cc','-O2',f,'-o',td+'/check'],check=True);subprocess.run([td+'/check'],check=True)
elif __name__=='__main__':runpy.run_path(str(p/'model-copy.py'))['build']('indexed-read',[(True,[2,10,16,26,39])],transform)
