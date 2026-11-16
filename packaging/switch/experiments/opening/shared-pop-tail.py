"""Factor repeated guest return sequences across functions, retaining each volatile pop."""
from pathlib import Path
from collections import Counter
import re,runpy,sys
p=Path(__file__).parent
units=[2,10,16,26]
pat=re.compile(r'(?m)^(?:    POP32\(esp, (?:edi|esi|ebp|ebx)\);\n){2,4}(?:    esp = ebp;\n    POP32\(esp, ebp\);\n)?    esp \+= (?:4|8|12|16); return; /\* ret \*/')
def transform(s,u):
 bodies=list(re.finditer(r'(?ms)^void \w+\(void\)\n\{.*?^\}',s))
 groups=Counter(m[0] for b in bodies if 'uint32_t ebp = 0;' in b[0] for m in pat.finditer(b[0]))
 selected={k:i for i,(k,n) in enumerate(sorted(groups.items())) if n>=8}
 if not selected:return s
 decl=''
 for raw,i in selected.items():
  name=f'ngb_pop_tail_{i}';body=raw.replace(' return; /* ret */','')
  # The original ebp destination is a discarded automatic local. Its volatile
  # guest load must still execute. No entry / checkpoint is added by helpers.
  frame='    esp = ebp;' in raw
  param='uint32_t ebp' if frame else 'void'
  local='' if frame else 'uint32_t ebp __attribute__((unused));'
  decl+=f'\nstatic void {name}({param}) asm(".L{name}");\nstatic __attribute__((noinline,noclone)) void {name}({param}){{{local}\n{body}\n}}\n'
 for b in reversed(bodies):
  if 'uint32_t ebp = 0;' not in b[0]:continue
  s=s[:b.start()]+pat.sub(lambda m:f'    ngb_pop_tail_{selected[m[0]]}({"ebp" if "    esp = ebp;" in m[0] else ""}); return;' if m[0] in selected else m[0],b[0])+s[b.end():]
 print('unit',u,'helpers',len(selected),'exits',sum(groups[k] for k in selected),flush=True)
 return s.replace('#include "recomp_funcs.h"','#include "recomp_funcs.h"\n'+decl,1)
if __name__=='__main__':
 if '--count' in sys.argv:
  for u in units:transform(Path(f'build/switch-runtime/gen/recomp_{u:04}.c').read_text(),u)
 else:runpy.run_path(str(p/'model-copy.py'))['build']('shared-pop-tail',[(True,units)],transform)
