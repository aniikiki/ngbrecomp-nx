"""Opening replay: cache the exclusive last eligible VA per page for 1..4 byte accesses.
The last three byte addresses conservatively use the original scalar fallback;
unmapped entries store zero, so VA zero never qualifies. Vector/other widths
use the old table. Keep the two tables in sync at all four mapping write sites."""
from pathlib import Path
import re,os,sys
base=Path('/work/build/switch-runtime')
full='--all-units' in sys.argv
d=base/'core-perf'/('opening-full-page' if full else 'opening-page-limit')
d.mkdir(exist_ok=True)
abi=Path('/work/packaging/switch/arm-registers');rt=abi.parent/'runtime'
def once(s,a,b):
 assert s.count(a)==1,a
 return s.replace(a,b)
for name,expected in [('vm.c',3),('contiguous.c',1)]:
 s=(rt/name).read_text()
 pre='uint32_t opening_end4[1u<<20];' if name=='vm.c' else 'extern uint32_t opening_end4[1u<<20];'
 s=once(s,'#include "guest_memory.h"','#include "guest_memory.h"\n'+pre)
 if name=='vm.c':
  s=once(s,'    memset(ngb_fast_page_bytes,','    memset(opening_end4,0,sizeof opening_end4);\n    memset(ngb_fast_page_bytes,')
 s,n=re.subn(r'ngb_fast_page_bytes\[([^\]]+)\] = ([^;]+);',lambda m:m[0]+' opening_end4['+m[1]+']=ngb_fast_page_bytes['+m[1]+'] ? (('+m[1]+')<<12)+4093u : 0;',s)
 assert n==expected
 (d/name).write_text(s)
s=(rt/'guest_memory.h').read_text()
needle='    if (__builtin_expect((address & 4095u) + bytes'
s=once(s,needle,'''    if (__builtin_constant_p(bytes) && bytes>=1 && bytes<=4) {
        if (__builtin_expect(address < reg_ends[address>>12],1))
            return (uintptr_t)ngb_fast_ram + (address & 0x7fffffffu);
        return ngb_guest_scalar_fallback(address,bytes);
    }
'''+needle)
(d/'template.h').write_text(s)
os.environ['NGB_REG_OUT']=str(d)
s=(abi/'compile.py').read_text()
s=once(s,"(r/'guest_memory.h').read_text()","(o/'template.h').read_text()")
s=once(s,'register uint16_t *reg_pages asm("x27");','register uint32_t *reg_ends asm("x27");')
s=once(s,'#define ngb_fast_page_bytes reg_pages','')
s=s.replace('x27,ngb_fast_page_bytes','x27,opening_end4').replace('x27,:lo12:ngb_fast_page_bytes','x27,:lo12:opening_end4')
if full:
 s,n=re.subn(r'^ns=\[[\d,]+\]$', 'ns=list(range(47))',s,flags=re.M);assert n==1
 numeric=r'(?:sub_|d3d_orig_)[0-9A-F]+'
 assert s.count(numeric)==2;s=s.replace(numeric,'(?:'+numeric+'|xbe_entry_point)')
exec(compile(s,'limit-build','exec'),{})
exec(compile((abi/'gates.py').read_text(),'limit-gates','exec'),{})
for f in d.glob('recomp_*.s'):f.unlink()
