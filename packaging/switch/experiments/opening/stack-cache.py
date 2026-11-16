"""Memoize one validated ordinary low guest stack page. The unsigned 64-bit
difference rejects addresses below the page and straddles in one comparison.
Page zero, MMIO, aliases and unmapped pages never populate the cache."""
import os,re,sys
from pathlib import Path
base=Path.cwd()/'build/switch-runtime';abi=Path.cwd()/'packaging/switch/arm-registers'
d=base/'core-perf/opening-stack-cache'
scan='--scan' in sys.argv
if not scan:d.mkdir(exist_ok=True)
vm=(abi.parent/'runtime/vm.c').read_text()
def once(s,k,val):
 assert s.count(k)==1,k
 return s.replace(k,val)
vm=once(vm,'static unsigned char *memory;', '''static unsigned char *memory;
uint64_t ngb_stack_page = UINT64_C(1)<<32;
uintptr_t ngb_stack_miss(uint32_t va,unsigned bytes){
 unsigned page=va>>12;
 if(va<NGB_RAM_BYTES && ngb_fast_page_bytes[page]==4096 && bytes<=4096u-(va&4095u)){
    ngb_stack_page=va & ~4095u;
    return (uintptr_t)ngb_fast_ram + va;
 }
 return ngb_guest_scalar(va,bytes);
}''')
for k in ('    memory = ngb_fast_ram = guest_ram;', '        ngb_fast_page_bytes[NGB_VM_BEGIN/PAGE + i] = 0;'):
 vm=once(vm,k,'    ngb_stack_page=UINT64_C(1)<<32;\n'+k)
if not scan:(d/'vm.c').write_text(vm)
types={'MEM32':'uint32_t','MEM16':'uint16_t','MEM8':'uint8_t','MEMF':'float','MEMD':'double','SMEM32':'int32_t','SMEM16':'int16_t','SMEM8':'int8_t','SMEM64':'int64_t'}
code="""
extern uint64_t ngb_stack_page;
extern uintptr_t ngb_stack_miss(uint32_t,unsigned);
static inline __attribute__((always_inline)) uintptr_t ngb_stack_addr(uint32_t va,unsigned bytes){
 if(__builtin_expect((uint64_t)va-ngb_stack_page <= 4096u-bytes,1))
    return (uintptr_t)ngb_fast_ram+va;
 return ngb_stack_miss(va,bytes);
}
#define OPEN_PUSH(sp,val) do{uint32_t _pv=(uint32_t)(val);(sp)-=4;*(volatile uint32_t*)ngb_stack_addr((sp),4)=_pv;}while(0)
#define OPEN_POP(sp,dst) do{(dst)=*(volatile uint32_t*)ngb_stack_addr((sp),4);(sp)+=4;}while(0)
"""
total=[0,0,0]
for i in (0,1,2,3,9,10,11,14,16,27,28,29,37,44):
 name=f'recomp_{i:04}.c';s=(base/'gen'/name).read_text()
 s=once(s,'#include "recomp_funcs.h"','#include "recomp_funcs.h"\n'+code)
 s,n=re.subn(r'\b('+'|'.join(types)+r')\((esp(?: [+-] (?:0x[0-9a-fA-F]+|\d+))?)\)',lambda m:f'(*(volatile {types[m[1]]}*)ngb_stack_addr({m[2]},sizeof({types[m[1]]})))',s);total[0]+=n
 for j,op in enumerate(('PUSH','POP'),1):
  s,n=re.subn(r'\b'+op+r'32\(esp,',f'OPEN_{op}(esp,',s);total[j]+=n
 if not scan:(d/name).write_text(s)
print('stack scalar, push, pop sites:',total,flush=True)
if scan:sys.exit()
os.environ['NGB_REG_OUT']=str(d)
s=(abi/'compile.py').read_text()
# Miss is an ordinary ABI call: preserve the original register publication in
# case its fallback reports a fault. Mapping writes never run on a render worker.
k=' sp.run(c,cwd=w,check=True)';s=once(s,k,' c[-1]=str(o/n)\n'+k)
exec(compile(s,'stack-cache','exec'),{})
exec(compile((abi/'gates.py').read_text(),'stack-cache-gates','exec'),{})
for pat in ('recomp_*.s','recomp_*.c'):
 for f in d.glob(pat):f.unlink()
