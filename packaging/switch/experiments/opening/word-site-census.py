"""Freeze a per-site candidate page after 30 flips; count exact matches in the held-out 90."""
import runpy
from pathlib import Path
p=Path(__file__).parent
units=[2,10,16,26,39]
def transform(s,u):
 k='#include "recomp_funcs.h"';assert s.count(k)==1
 s=s.replace(k,k+f'''
extern void ws_observe(unsigned,unsigned,unsigned);
static __attribute__((always_inline)) inline uintptr_t ws_addr(uint32_t a,unsigned site){{
 if(!ngb_static_image_span(a,4))ws_observe({units.index(u)}u,site,a);
 return ngb_guest_scalar(a,4);
}}
#undef MEM32
#define MEM32(a) (*(volatile uint32_t *)ws_addr((uint32_t)(a),__COUNTER__))
''')
 return s+'\n_Static_assert(__COUNTER__<65536,"word site capacity");\n'
if __name__=='__main__':runpy.run_path(str(p/'model-copy.py'))['build']('word-site-census',[(True,units)],transform)
