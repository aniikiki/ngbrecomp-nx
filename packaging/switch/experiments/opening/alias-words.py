"""Host replay only. Preserve every mapping test; omit the alias-bit AND for an already verified normal page."""
from pathlib import Path
import runpy
p=Path(__file__).parent
def transform(s,u):
 k='#include "recomp_funcs.h"';assert s.count(k)==1
 h='''
static inline __attribute__((always_inline)) uintptr_t aw_addr(uint32_t a,size_t n){
 if(ngb_static_image_span(a,n)&&ngb_fast_ram)return (uintptr_t)ngb_fast_ram+a;
 if(__builtin_expect(a<reg_ends[a>>12],1))return (uintptr_t)ngb_fast_ram+a;
 return ngb_guest_scalar_fallback(a,n);
}
'''
 for bits in (8,16,32):
  h+=f'#undef MEM{bits}\n#define MEM{bits}(addr) (*(volatile uint{bits}_t*)aw_addr((uint32_t)(addr),{bits//8}))\n'
 return s.replace(k,k+'\n'+h)
if __name__=='__main__':runpy.run_path(str(p/'model-copy.py'))['build']('alias-words',[(True,[2,10,16,26,39])],transform)
