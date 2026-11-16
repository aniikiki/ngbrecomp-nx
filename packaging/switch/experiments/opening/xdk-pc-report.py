"""Group exclusive delivered thread-PC samples by outer D3D scope and actual leaf."""
from pathlib import Path
from collections import Counter
import bisect,re
d=Path('build/switch-runtime/core-perf/opening-xdk-pc-scope')
sy={}
for row in (d/'symbols.txt').read_text().splitlines():
 a,n,_,name=row.split(maxsplit=3);a,n=int(a,16),int(n,16)
 if n>sy.get(a,(0,''))[0]:sy[a]=(n,name)
keys=sorted(sy)
def resolve(a):
 j=bisect.bisect_right(keys,a)-1
 if j>=0 and a-keys[j]<sy[keys[j]][0]:return sy[keys[j]][1]
 return '<external/unknown>'
for i in range(1,5):
 s=(d/f'run-{i}.log').read_text()
 assert 'reason=verified 120 original demo frames' in s
 rows=re.findall(r'^\[D3D_SCOPE_PC\] (\d+) (\d+) ([0-9a-f]+)$',s,re.M)
 assert len(rows)==int(re.search(r'\[FRAME_PC_COUNT\] (\d+)',s)[1])
 for lo,hi in ((1,30),(31,120)):
  inside=Counter();outside=Counter()
  for f,depth,pc in rows:
   if lo<=int(f)<=hi:(inside if int(depth) else outside)[resolve(int(pc,16))]+=1
  assert inside and outside
  print(i,lo,hi,'inside/outside',sum(inside.values()),sum(outside.values()),'outside named generated',sum(n for k,n in outside.items() if re.match(r'(?:ngb_reg_)?(?:sub_|d3d_orig_)',k)), 'outside top',outside.most_common(6))
