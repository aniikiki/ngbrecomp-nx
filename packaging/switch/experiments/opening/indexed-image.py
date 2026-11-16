"""Specialize indexed static-image tables. Bound the *index*, before any
32-bit wrapping, so the predicted branch needs no page table load or alias
mask. Wild or negative indices still use exactly the ordinary guest access."""
from pathlib import Path
import os,re,sys
root=Path.cwd();base=root/'build/switch-runtime';abi=root/'packaging/switch/arm-registers'
d=base/'core-perf/opening-indexed-image';d.mkdir(exist_ok=True)
w={'MEM8':1,'SMEM8':1,'MEM16':2,'SMEM16':2,'MEM32':4,'SMEM32':4,'MEMF':4,'MEMD':8,'SMEM64':8}
typ={'MEM8':'uint8_t','SMEM8':'int8_t','MEM16':'uint16_t','SMEM16':'int16_t','MEM32':'uint32_t','SMEM32':'int32_t','MEMF':'float','MEMD':'double','SMEM64':'int64_t'}
pat=r'\b('+'|'.join(w)+r')\((e(?:ax|bx|cx|dx|si|di|bp)) \* ([1248]) \+ (0x[0-9A-Fa-f]+)\)'
n=0
for u in (0,1,2,3,9,10,11,14,16,27,28,29,37,44):
 name=f'recomp_{u:04}.c';s=(base/'gen'/name).read_text()
 def repl(m):
  global n
  op,reg,scale,b=m.groups();ba=int(b,16);sc=int(scale)
  if not 0x8000<=ba<=0x01000000-w[op]:return m[0]
  n+=1
  limit=(0x01000000-ba-w[op])//sc
  ptr=f'open_indexed((uint32_t){reg},{sc}u,{b}u,{limit}u,{w[op]}u)'
  return f'(*(volatile {typ[op]} *){ptr})'
 s=re.sub(pat,repl,s)
 k='#include "recomp_funcs.h"';assert s.count(k)==1
 s=s.replace(k,k+'''
static __attribute__((always_inline)) inline uintptr_t open_indexed(uint32_t idx,uint32_t scale,uint32_t base,uint32_t max_idx,unsigned bytes){
 uint32_t va=base+scale*idx;
 if(__builtin_expect(idx<=max_idx,1) && ngb_fast_ram) return (uintptr_t)ngb_fast_ram+va;
 return ngb_guest_scalar(va,bytes);
}
''')
 if '--scan' not in sys.argv:(d/name).write_text(s)
print(n,'indexed table accesses',flush=True)
if '--scan' in sys.argv:sys.exit()
os.environ['NGB_REG_OUT']=str(d)
s=(abi/'compile.py').read_text();k=' sp.run(c,cwd=w,check=True)';assert s.count(k)==1
exec(compile(s.replace(k,' c[-1]=str(o/n)\n'+k),'indexed-image','exec'),{})
exec(compile((abi/'gates.py').read_text(),'indexed-gates','exec'),{})
for pat in ('recomp_*.s','recomp_*.c'):
 for f in d.glob(pat):f.unlink()
