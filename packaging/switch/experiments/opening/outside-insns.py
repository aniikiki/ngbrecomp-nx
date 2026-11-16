"""Classify actual sampled instructions outside the nested Direct3D scope."""
from pathlib import Path
from collections import Counter
import re
d=Path('build/switch-runtime/core-perf/opening-xdk-pc-scope')
code={}
for line in (d/'sampled-insns.txt').read_text().splitlines():
 pc,name,off,op,*args=line.split();code[int(pc,16)]=(name,op,' '.join(args))
for lo,hi in ((1,30),(31,120)):
 total=Counter();owners=Counter();secondary=Counter();direct=Counter()
 for i in range(1,5):
  text=(d/f'run-{i}.log').read_text()
  assert 'reason=verified 120 original demo frames' in text
  bins=Counter()
  for f,depth,pc in re.findall(r'^\[D3D_SCOPE_PC\] (\d+) (\d+) (\w+)$',text,re.M):
   if not lo<=int(f)<=hi:continue
   if int(depth):bins['inside']+=1;continue
   name,op,args=code.get(int(pc,16),('','',''))
   if not re.match(r'^(?:ngb_reg_)?(?:sub_|d3d_orig_)[0-9A-F]+',name):
    bins['outside other']+=1;continue
   owners[name]+=1
   if op.startswith(('ld','st')):
    key=next((k for k in ('x27','x26','x28','sp','x29') if '['+k in args),'other memory')
    if key=='x27':
     addr='fixed' if not re.search(r'\[x27, [wx]\d+',args) else 'indexed'
     secondary[addr]+=1; direct[name,addr]+=1
   elif op.startswith(('b.','cb','tb')) or op in ('b','bl','blr','ret','br'):key='control'
   else:key='arithmetic/other'
   bins['outside guest '+key]+=1
  print(lo,hi,i,dict(bins));total+=bins
 print('all',total,'x27',secondary,'x27 owners',direct.most_common(12),'guest owners',owners.most_common(8))
