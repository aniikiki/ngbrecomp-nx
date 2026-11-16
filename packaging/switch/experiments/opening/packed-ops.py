from pathlib import Path
import os,re
root=Path('/work');base=root/'build/switch-runtime';abi=root/'packaging/switch/arm-registers'
d=base/'core-perf/opening-packed-ops';d.mkdir(exist_ok=True)
h=Path(__file__).with_suffix('.h').read_text()
for u in (0,1,2,3,9,10,11,14,16,27,28,29,37,44):
 name=f'recomp_{u:04}.c';s=(base/'gen'/name).read_text();k='#include "recomp_funcs.h"';assert s.count(k)==1
 # A variable shuffle selector needs the original runtime implementation.
 for line in s.splitlines():
  if 'XMM_SHUFFLE(' in line:assert re.search(r', (0x[0-9a-fA-F]+|\d+)\);',line),line
 (d/name).write_text(s.replace(k,k+'\n'+h))
os.environ['NGB_REG_OUT']=str(d)
s=(abi/'compile.py').read_text();k=' sp.run(c,cwd=w,check=True)'
s=s.replace(k,' c[-1]=str(o/n)\n'+k)
exec(compile(s,'packed-abi','exec'),{})
exec(compile((abi/'gates.py').read_text(),'packed-gates','exec'),{})
for pat in ('recomp_*.s','recomp_*.c'):
 for f in d.glob(pat):f.unlink()
