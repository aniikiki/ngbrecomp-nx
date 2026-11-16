"""Count interrupted instructions, not time inside a callee or entry frequencies."""
from bisect import bisect_right
from collections import Counter
from pathlib import Path
import re
p=Path('build/switch-runtime/core-perf')
names=set(re.findall(r'^\.global (\w+)$',(p/'opening-full-page/entry.S').read_text(),re.M))
for profile in ('compact','copy'):
 d=p/('opening-'+profile+'-profile');sy={}
 for l in (d/'symbols.txt').read_text().splitlines():
  a,n,_,fn=l.split(maxsplit=3);a,n=int(a,16),int(n,16)
  if n>sy.get(a,(0,''))[0]:sy[a]=(n,fn)
 keys=sorted(sy);late=Counter()
 def locate(pc):
  j=bisect_right(keys,pc)-1
  if j<0:return ''
  base=keys[j];n,fn=sy[base];return fn if pc-base<n else ''
 for i in range(1,5):
  s=(d/f'run-{i}.log').read_text();assert 'verified 120 original demo frames' in s
  rows=re.findall(r'^\[FRAME_PC\] (\d+) (\w+)$',s,re.M)
  assert len(rows)==int(re.search(r'\[FRAME_PC_COUNT\] (\d+)',s)[1])
  for f,pc in rows:
   if 31<=int(f)<=120:
    fn=locate(int(pc,16));late['all']+=1
    if fn in names:late['public']+=1;late['public XDK' if fn.startswith('d3d_orig_') else 'public game']+=1
    elif fn=='ngb_gate_indirect':late['indirect gate']+=1
 print(profile,dict(late))
