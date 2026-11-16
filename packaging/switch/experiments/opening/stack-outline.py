"""Keep the measured stack guard but share its uncommon original lookup path in each unit."""
from pathlib import Path
import runpy
p=Path(__file__).parent
base=runpy.run_path(str(p/'stack-prefix.py'))
def transform(s,u):
 t=base['transform'](s,u)
 a='static inline __attribute__((always_inline)) uintptr_t sw_addr'
 k=' return ngb_guest_scalar(va,4);'
 assert t.count(a)==t.count(k)==1
 return t.replace(k,' return sw_miss(va);').replace(a,'static __attribute__((noinline,noclone,cold)) uintptr_t sw_miss(uint32_t va){return ngb_guest_scalar(va,4);}\n'+a)
if __name__=='__main__':
 runpy.run_path(str(p/'model-copy.py'))['build']('stack-outline',[(True,[2,10,16,26,39])],transform)
