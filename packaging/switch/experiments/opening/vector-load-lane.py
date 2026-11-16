"""Ask GCC to keep the existing 16-byte memcpy result in a SIMD register on ordinary-page reads."""
from pathlib import Path
import runpy
p=Path(__file__).parent;b=Path('build/switch-runtime')
def transform(s,u):
 d=b/'core-perf/opening-vector-load-lane'
 h=(b/'gen/recomp_types.h').read_text()
 k='        __builtin_memcpy(&r, ngb_fast_ram + (addr & 0x7fffffffu), sizeof(r));'
 assert h.count(k)==1
 h=h.replace(k,'''    {
        typedef unsigned char Vec16 __attribute__((vector_size(16)));
        Vec16 v;__builtin_memcpy(&v,ngb_fast_ram+(addr&0x7fffffffu),16);
        __asm__("" : "+w"(v));
        __builtin_memcpy(&r,&v,16);
    }''')
 (d/'recomp_types.h').write_text(h)
 (d/'recomp_funcs.h').write_bytes((b/'gen/recomp_funcs.h').read_bytes())
 return s
if __name__=='__main__':runpy.run_path(str(p/'model-copy.py'))['build']('vector-load-lane',[(False,[0,28,29])],transform)
