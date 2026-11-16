"""Record actual generated guest stack pushes/pops (not function-entry ESP)."""
from pathlib import Path
import runpy
p=Path(__file__).parent
def transform(s,u):
 k='#include "recomp_funcs.h"';assert s.count(k)==1
 return s.replace(k,k+'''
extern void sw_observe(unsigned va,unsigned op);
#undef PUSH32
#define PUSH32(sp,val) do { uint32_t _pv=(uint32_t)(val); (sp)-=4; sw_observe((sp),0); MEM32(sp)=_pv; } while(0)
#undef POP32
#define POP32(sp,dst) do { sw_observe((sp),1); (dst)=MEM32(sp); (sp)+=4; } while(0)
''')
if __name__=='__main__':
 runpy.run_path(str(p/'model-copy.py'))['build']('stack-window',[(True,[2,10,16,26,39])],transform)
