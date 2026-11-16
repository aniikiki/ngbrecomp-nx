"""Safe region translation, hoisting coverage, crossing and alias checks
to VM map changes. Ineligible regions retain original per-page fallback."""
from pathlib import Path
import re,os
base=Path('/work/build/switch-runtime')
d=base/'core-perf/opening-region-bias';d.mkdir(exist_ok=True)
abi=Path('/work/packaging/switch/arm-registers');rt=abi.parent/'runtime'
for name,expected in [('vm.c',3),('contiguous.c',1)]:
 s=(rt/name).read_text()
 pre=Path(__file__).with_name('region-bias.inc').read_text() if name=='vm.c' else 'void ngb_region_changed(unsigned);'
 s=s.replace('#include "guest_memory.h"','#include "guest_memory.h"\n'+pre)
 # extern declarations for fast RAM and page lengths come from guest_memory.h
 if name=='vm.c':s=s.replace('    memset(ngb_fast_page_bytes,','    memset(ngb_region_bias,0,sizeof ngb_region_bias);\n    memset(ngb_fast_page_bytes,')
 s,n=re.subn(r'ngb_fast_page_bytes\[([^\]]+)\] = ([^;]+);',lambda m:m[0]+' ngb_region_changed('+m[1]+');',s)
 assert n==expected
 (d/name).write_text(s)
s=(rt/'guest_memory.h').read_text()
s=s.replace('    if (__builtin_expect((address & 4095u) + bytes', '''    if (__builtin_constant_p(bytes) && bytes && bytes<=16) {
        uintptr_t bias=reg_bias[address>>16];
        if (__builtin_expect(bias!=0,1)) return bias+address;
    }
    if (__builtin_expect((address & 4095u) + bytes''')
s=s.replace('    if (__builtin_expect((address & 4095u) + 16u','    uintptr_t bias=reg_bias[address>>16];\n    if (__builtin_expect(bias!=0,1)) return (void *)(bias+address);\n    if (__builtin_expect((address & 4095u) + 16u')
(d/'template.h').write_text(s)
os.environ['NGB_REG_OUT']=str(d)
s=(abi/'compile.py').read_text().replace("(r/'guest_memory.h').read_text()","(o/'template.h').read_text()").replace('register uint16_t *reg_pages asm("x27");','register uintptr_t *reg_bias asm("x27");').replace('#define ngb_fast_page_bytes reg_pages','')
s=s.replace('x27,ngb_fast_page_bytes','x27,ngb_region_bias').replace('x27,:lo12:ngb_fast_page_bytes','x27,:lo12:ngb_region_bias')
exec(compile(s,'region-build','exec'),{})
exec(compile((abi/'gates.py').read_text(),'region-gates','exec'),{})
for f in d.glob('recomp_*.s'):f.unlink()
