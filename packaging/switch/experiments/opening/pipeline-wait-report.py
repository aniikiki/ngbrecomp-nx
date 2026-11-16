"""Intersect measured intervals; do not charge parallel creation outside waits."""
from pathlib import Path
import re
s=Path('build/switch-runtime/core-perf/opening-pipeline-wait/budget.log').read_text()
assert 'verified 120 original demo frames' in s and '[PW_LOST] 0' in s
f=dict((int(i),int(t)) for i,t in re.findall(r'^\[PW_FLIP\] (\d+) (\d+)$',s,re.M))
assert set(f)==set(range(121)) and all(f[i]<f[i+1] for i in range(120))
events=[tuple(map(int,m)) for m in re.findall(r'^\[PW_EVENT\] (\d+) (\d+) (\d+)$',s,re.M)]
def spans(k,a,b):
 r=[]
 for lo,hi in sorted((max(a,l),min(b,h)) for kind,l,h in events if kind==k and l<b and h>a):
  if r and lo<=r[-1][1]: r[-1]=(r[-1][0],max(hi,r[-1][1]))
  else:r.append((lo,hi))
 return r
for a,b in ((0,1),(1,2),(2,30),(30,120)):
 w,p=[spans(k,f[a],f[b]) for k in (0,1)]
 intersect=sum(max(0,min(y,h)-max(x,l)) for x,y in w for l,h in p)
 print(a+1,b,'measured wait, creation, overlap ms:',*[round(x/1e6,3) for x in (sum(y-x for x,y in w),sum(y-x for x,y in p),intersect)])
