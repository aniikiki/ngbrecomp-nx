"""Offline experiment: one translated pointer, one aligned-and-mapped predicate."""
from pathlib import Path
import re
base=Path('/work/build/switch-runtime')
d=base/'opt050/bias';d.mkdir(parents=True,exist_ok=True)
host=d/'host-src';host.mkdir(exist_ok=True)
rt=Path('/work/packaging/switch/runtime');abi=rt.parent/'arm-registers'
s=(rt/'guest_memory.h').read_text()
anchor='static inline __attribute__((always_inline)) uintptr_t ngb_guest_scalar('
s=s.replace(anchor,'''extern uintptr_t ngb_aligned_bias[1u<<20];
/* Mapped bias + unsigned Xbox VA is the host address. Invalid entries keep
 * bit 63 set after any 32-bit addition. Low bits reject an unaligned access,
 * so a hot access cannot straddle either a protection or allocation boundary. */
static inline __attribute__((always_inline)) uintptr_t ngb_bias_address(uint32_t va){
    return ngb_aligned_bias[va>>12] + (uintptr_t)va;
}
'''+anchor)
a=s.index('    if (__builtin_expect((address & 4095u) + bytes');b=s.index('    return ngb_guest_scalar_fallback(address, bytes);',a)
s=s[:a]+'''    if (__builtin_constant_p(bytes) && (bytes==1||bytes==2||bytes==4||bytes==8||bytes==16)){
        uintptr_t p=ngb_bias_address(address);
        if(__builtin_expect(!(p & (UINT64_C(0x8000000000000000)|(bytes-1))),1))return p;
    }
'''+s[b:]
a='    if (__builtin_expect((address & 4095u) + 16u <= ngb_fast_page_bytes[address >> 12], 1))'
s=s.replace(a,'''    uintptr_t pfast=ngb_bias_address(address);
    if(__builtin_expect(!(pfast & UINT64_C(0x800000000000000f)),1))return (void*)pfast;
'''+a)
(d/'guest-template.h').write_text(s)
state='''extern uintptr_t ngb_aligned_bias[1u<<20];
static inline void refresh_one_bias(unsigned i) {
    ngb_aligned_bias[i]=ngb_fast_page_bytes[i]==4096 && ngb_fast_ram &&
        !((uintptr_t)ngb_fast_ram&15u) && (uintptr_t)ngb_fast_ram < (UINT64_C(1)<<63)-(128u<<20) ?
        (uintptr_t)ngb_fast_ram-((uintptr_t)(i&(1u<<19))<<12) :
        UINT64_C(0x8000000000000000);
}
'''
for name,expected in [('vm.c',3),('contiguous.c',1)]:
    s=(rt/name).read_text().replace('#include "guest_memory.h"','#include "guest_memory.h"\n'+state)
    if name=='vm.c':
        s=s.replace('static unsigned char *memory;', 'uintptr_t ngb_aligned_bias[1u<<20];\nstatic unsigned char *memory;')
        s=s.replace('    memset(ngb_fast_page_bytes,','    memset(ngb_aligned_bias,0x80,sizeof ngb_aligned_bias);\n    memset(ngb_fast_page_bytes,')
    s,n=re.subn(r'ngb_fast_page_bytes\[([^\]]+)\] = ([^;]+);',lambda m:m[0]+' refresh_one_bias('+m[1]+');',s)
    assert n==expected
    (host/name).write_text(s)
# Compile with the same fourteen units and private ABI as 0.51, retaining
# original sources untouched. x27 now holds the biased pointer table.
s=(abi/'compile.py').read_text().replace("o=w.parent/'native-regs'","o=w.parent/'opt050/bias'").replace("(r/'guest_memory.h').read_text()","(o/'guest-template.h').read_text()")
s=s.replace('register uint16_t *reg_pages asm("x27");','register uintptr_t *reg_bias asm("x27");')
s=s.replace('#define ngb_fast_page_bytes reg_pages','')
s=s.replace("(o/'guest_memory.h').write_text(mem)",'''mem=mem.replace('return ngb_aligned_bias[va>>12]', 'return reg_bias[va>>12]')
(o/'guest_memory.h').write_text(mem)''')
s=s.replace('adrp x27,ngb_fast_page_bytes','adrp x27,ngb_aligned_bias').replace('add x27,x27,:lo12:ngb_fast_page_bytes','add x27,x27,:lo12:ngb_aligned_bias')
exec(compile(s,'bias-compile','exec'),{'__name__':'__main__'})
s=(abi/'gates.py').read_text().replace('/switch-runtime/native-regs','/switch-runtime/opt050/bias')
exec(compile(s,'bias-gates','exec'),{'__name__':'__main__'})
