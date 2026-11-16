from collections import Counter
from pathlib import Path
import bisect,re
d=Path('build/switch-runtime/core-perf/opening-low-prefix-sample')
sy={}
for l in (d/'symbols.txt').read_text().splitlines():
 a,n,_,name=l.split(maxsplit=3);a,n=int(a,16),int(n,16)
 if n>sy.get(a,(0,''))[0]:sy[a]=(n,name)
keys=sorted(sy)
for i in (1,2):
 s=(d/f'run-{i}.log').read_text();assert 'verified 120 original demo frames' in s
 for lo,hi in [(1,30),(31,120)]:
  cats=Counter();ends=set()
  for f,pc,pg,end in re.findall(r'^\[LOW_PREFIX\] (\d+) (\w+) (\w+) (\w+)$',s,re.M):
   if not lo<=int(f)<=hi:continue
   pc,pg,end=(int(v,16) for v in (pc,pg,end));j=bisect.bisect_right(keys,pc)-1
   if j<0:continue
   a=keys[j];n,name=sy[a]
   if pc>=a+n or not name.startswith(('ngb_reg_sub_','ngb_reg_d3d_orig_')):continue
   ends.add(end)
   cats['image' if 8<=pg<min(end,4096) else 'VM prefix' if 4096<=pg<end else 'outside']+=1
  assert cats
  print(i,lo,hi,dict(cats),'prefix endpoints in pages',sorted(ends))
