"""Supplement the run-level A/B with overlap in scene time and draw count.
Match only within a run pair, without replacing frames, and disclose coverage.
A similar draw count does not make all non-render game logic identical."""
from pathlib import Path
from itertools import groupby
from statistics import mean,median
import re,sys
d=Path(sys.argv[1]);tag=sys.argv[2]
for i in range(1,5):
 def read(arm):
  s=(d/f'{tag}-{arm}-{i}.log').read_text()
  assert '[RESULT] status=1 reason=verified 120 original demo frames' in s
  a=[tuple(map(int,m)) for m in re.findall(r'^\[OPEN_PAIR\] (\d+) \d+ (\d+) (\d+)$',s,re.M)]
  assert [x[0] for x in a]==list(range(1,121))
  return a[30:]
 a,b=read('original'),read('limit')
 # Exact draw count, at most 6 flips apart. Dynamic programming per draw count
 # maximizes number of pairs and then minimizes total temporal separation.
 from functools import lru_cache
 out=[]
 for draw in sorted(set(r[2] for r in a)&set(r[2] for r in b)):
  aa=[r for r in a if r[2]==draw];bb=[r for r in b if r[2]==draw]
  @lru_cache(None)
  def opt(j,k):
   if j==len(aa) or k==len(bb):return (0,0,())
   best=max(opt(j+1,k),opt(j,k+1))
   dt=abs(aa[j][0]-bb[k][0])
   if dt<=6:
    n,v,pairs=opt(j+1,k+1);best=max(best,(n+1,v-dt,((j,k),)+pairs))
   return best
  out.extend((aa[j],bb[k]) for j,k in opt(0,0)[2])
 ms=[(x[1]-y[1])/1e6 for x,y in out]
 print(tag,i,'exact draw / nearby flip pairs',len(ms),'of 90','mean/median savings ms',
       round(mean(ms),4) if ms else None,round(median(ms),4) if ms else None)
