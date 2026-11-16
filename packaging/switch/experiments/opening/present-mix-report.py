"""Pair nearby logical pictures by draw sequence fingerprint, never by timings.
Timings are reported only as sensitivities; a geometry signature omits game state.
"""
from pathlib import Path
from functools import lru_cache
from statistics import mean,median
import re
d=Path('build/switch-runtime/core-perf/opening-present-mix')
def read(name):
 s=(d/(name+'.log')).read_text();assert 'verified 120 original demo frames' in s
 r=[(int(a),int(b),int(n),int(v),h,int(t),int(e),int(p)) for a,b,n,v,h,t,e,p in re.findall(r'^\[PRESENT_MIX\] (\d+) (\d+) (\d+) (\d+) ([0-9a-f]{16}) (\d+) (\d+) (\d+)$',s,re.M)]
 assert len(r)>100 and all(b==v[0] for (_,b,*_),v in zip(r,r[1:]))
 return [v for v in r if v[0]>=30 and v[1]<120]
def matching(a,b):
 @lru_cache(None)
 def best(i,j):
  if i==len(a) or j==len(b):return (0,0,())
  res=max(best(i+1,j),best(i,j+1))
  dist=abs(a[i][1]-b[j][1])
  if dist<=6 and a[i][2:5]==b[j][2:5]:
   n,c,seq=best(i+1,j+1);res=max(res,(n+1,c-dist,((i,j),)+seq))
  return res
 return best(0,0)[2]
if __name__=='__main__':
 for i in (1,2):
  a,b=(read(f'{arm}-{i}') for arm in ('base','retained'))
  m=matching(a,b);print(i,'complete presents',len(a),len(b),'matched',len(m))
  print('all late CPU base/retained ms:',*[round(mean(x[5] for x in arm)/1e6,4) for arm in (a,b)])
  if m:
   dt=[(a[k][5]-b[j][5])/1e6 for k,j in m]
   print('matched savings mean/median ms:',round(mean(dt),4),round(median(dt),4),'median absolute entry/poll differences:',*[median(abs(a[k][v]-b[j][v]) for k,j in m) for v in (6,7)])
 for arm in ('base','retained'):
  a,b=read(arm+'-1'),read(arm+'-2')
  print(arm,'repeatability, same ordered draw parameters',len(matching(a,b)),'of',len(a),len(b))
