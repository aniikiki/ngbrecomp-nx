"""Attribute only actual samples inside known symbol sizes of the same ELF.
Shared libraries are intentionally outside the non-PIE executable map."""
from pathlib import Path
from collections import Counter
from bisect import bisect_right
import re,sys
d=Path('build/switch-runtime/core-perf/opening-frame-pc')
s=(d/(sys.argv[1] if len(sys.argv)>1 else 'distribution.log')).read_text()
modules={(int(f),int(pc,16)):(path.split('/')[-1],sym) for f,pc,path,sym in re.findall(r'^\[FRAME_MODULE\] (\d+) ([0-9a-f]+) [0-9a-f]+ (\S+) (\S+)$',s,re.M)}
assert 'verified 120 original demo frames' in s
symbols={}
for line in (d/('initial-symbols.txt' if len(sys.argv)>1 and sys.argv[1]=='distribution-initial.log' else 'lr-symbols.txt' if len(sys.argv)>1 and sys.argv[1]=='distribution-lr.log' else 'module-symbols.txt' if len(sys.argv)>1 and sys.argv[1]=='distribution-modules.log' else 'text-symbols.txt')).read_text().splitlines():
 a,n,_,name=line.split(maxsplit=3);a=int(a,16);n=int(n,16)
 if n and n>symbols.get(a,(0,''))[0]:symbols[a]=n,name
keys=sorted(symbols)
counts=[Counter(),Counter()];domain=[Counter(),Counter()]
for frame,pc in re.findall(r'^\[FRAME_PC\] (\d+) ([0-9a-f]+)$',s,re.M):
 pc=int(pc,16);f=int(frame);assert 1<=f<=120
 i=bisect_right(keys,pc)-1
 name='unmapped'
 if i>=0:
  a=keys[i];n,symbol=symbols[a]
  if pc<a+n:name=symbol
 if name=='unmapped' and (f,pc) in modules:
  mod,sym=modules[f,pc]
  name='module:'+mod+':'+sym
 w=int(f>30);counts[w][name]+=1
 cat=('unmapped' if name=='unmapped' else 'module' if name.startswith('module:') else 'checkpoint' if name=='ngb_reg_checkpoint' else 'guest' if re.match(r'(?:ngb_reg_|sub_|d3d_orig_|xbe_entry_point)',name) else 'recorder' if 'Recorded' in name else 'other named')
 domain[w][cat]+=1
n,lost=map(int,re.search(r'^\[FRAME_PC_COUNT\] (\d+) (\d+)$',s,re.M).groups())
assert n==sum(sum(c.values()) for c in counts)
print('unattributed overruns / dropped:',lost)
for title,c,g in zip(('1..30','31..120'),counts,domain):
 print(title,sum(c.values()),dict(g),'top exact functions:',c.most_common(14))
