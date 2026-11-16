"""Apply fault-guarded direct memory to dynamic scalar accesses, beyond the stack.
Keep x27's page table: place the sparse view at a fixed delta from ordinary RAM.
Non-matching expressions (esp. pointer-taking and RMW) keep the original helper.
Linux runner only; no dependence on Switch virtual-address reservation policy."""
from pathlib import Path
import re
base=Path('/work/build/switch-runtime');d=base/'opt050/scalar-view';d.mkdir(exist_ok=True);abi=Path('/work/packaging/switch/arm-registers')
header=['#include "guest_memory.h"','#define VIEW_BASE ((uintptr_t)ngb_fast_ram + (1ull<<32))','#define FIXUP "\\n.pushsection ngb_fault,\\"a\\",@progbits\\n.balign 4\\n.long 1b-.\\n.long %l[slow]-.\\n.popsection\\n"']
for kind,typ,inst,reg in [('8','uint8_t','b','%w'),('16','uint16_t','h','%w'),('32','uint32_t','','%w'),('F','float','','%s')]:
 cl='w' if kind=='F' else 'r'
 for store in [False,True]:
  t=typ if not store else 'void';op=('str' if store else 'ldr')+inst
  name=('put' if store else 'get')+kind
  header += [f'static inline __attribute__((always_inline)) {t} view_{name}(uint32_t a'+(f',{typ} v' if store else '')+'){',
   ('' if store else f'{typ} v;')+f'asm goto volatile("1: {op} {reg}0,[%1,%w2,uxtw]" FIXUP '+(f'::"{cl}"(v)' if store else f':"={cl}"(v):')+(',' if store else '')+'"r"(VIEW_BASE),"r"(a):"memory":slow);',
   'return;' if store else 'return v;',f'slow: '+(f'MEM{kind}(a)=v;' if store else f'return MEM{kind}(a);')+'}']
(d/'direct.h').write_text('\n'.join(header)+'\n')
count=[0,0];ns=[0,1,2,3,9,10,11,14,16,27,28,29,37,44]
for n in ns:
 name=f'recomp_{n:04}.c';s=(base/'gen'/name).read_text();tag='#include "recomp_funcs.h"';assert s.count(tag)==1
 s=s.replace(tag,tag+'\n#include "direct.h"')
 addr=r'(?:e(?:ax|bx|cx|dx|si|di|bp|sp))(?: [+-] (?:-?(?:0x[0-9a-fA-F]+|[0-9]+)|e(?:ax|bx|cx|dx|si|di|bp|sp)))*'
 def load(m):
  count[0]+=1;return m[1]+f'view_get{m[2]}({m[3]})'+m[4]
 def store(m):
  count[1]+=1;return m[1]+f'view_put{m[2]}({m[3]}, {m[4]});'
 s=re.sub(r'(?m)^(\s*)MEM(8|16|32|F)\(('+addr+r')\) = ([^;\n]+);',store,s)
 # Never rewrite lvalues, compound assignments, address-taken accesses, or comments.
 s=re.sub(r'( = |\+= |-= |\*= |/='+' |ZX8\\(|ZX16\\(|LO8\\(|LO16\\(|, | = \\(uint32_t\\)\\(| [+*/-] )(?:MEM)(8|16|32|F)\\(('+addr+r')\)([;), ])',load,s)
 (d/name).write_text(s)
print('rewritten read/write source sites',count,flush=True)
s=(abi/'compile.py').read_text().replace("o=w.parent/'native-regs'","o=w.parent/'opt050/scalar-view'").replace(" sp.run(c,cwd=w,check=True)"," c[-1]=str(o/n)\n sp.run(c,cwd=w,check=True)",1)
exec(compile(s,'scalar-view','exec'),{'__name__':'__main__'})
s=(abi/'gates.py').read_text().replace('/switch-runtime/native-regs','/switch-runtime/opt050/scalar-view');exec(compile(s,'scalar-gates','exec'),{'__name__':'__main__'})
