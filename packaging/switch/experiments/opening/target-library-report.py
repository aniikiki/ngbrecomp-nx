"""Compare complete present intervals by run; report same-arm repeat spread separately."""
from pathlib import Path
from statistics import mean
from itertools import combinations
import sys
d=Path('build/switch-runtime/core-perf/opening-present-combined')
def read(path):
 text=path.read_text();assert 'reason=verified 120 original demo frames' in text
 r={}
 for l in text.splitlines():
  v=l.split()
  if v[:1]==['[PRESENT_MIX]'] and int(v[1])+1==int(v[2]) and 1<=int(v[2])<120:
   k=int(v[2]);assert k not in r;r[k]=(tuple(v[3:6]),int(v[6])/1e6)
 assert set(r)==set(range(1,120));return r
def compare(x,y,lo,hi):
 ids=list(range(lo,hi+1));common=[k for k in ids if x[k][0]==y[k][0]]
 raw=mean(x[k][1]-y[k][1] for k in ids)
 return [round(raw,5),len(common),round(mean(x[k][1]-y[k][1] for k in common),5) if common else None]
if __name__=='__main__':
 runs={arm:[read(d/f'targetlibs-{arm}-{i}.log') for i in (1,2,3)] for arm in ('base','retained','split')}
 for lo,hi in [(1,30),(31,119),(1,119)]:
  print('present intervals',lo,hi)
  for arm,xs in runs.items():
   means=[mean(x[k][1] for k in range(lo,hi+1)) for x in xs]
   print(arm,'run means ms',[round(t,5) for t in means],'same-arm range',round(max(means)-min(means),5))
  for a,b in combinations(runs,2):
   print(a,'minus',b,'[full mean, matched count, matched mean] per round',
         [compare(x,y,lo,hi) for x,y in zip(runs[a],runs[b])])
