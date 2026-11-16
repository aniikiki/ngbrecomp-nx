"""Compare only corresponding complete Present intervals; host CPU ns are not device time."""
from pathlib import Path
import re
from statistics import mean, median
d=Path('build/switch-runtime/core-perf/opening-rng-correspondence')
def read(name):
 s=(d/('seed-'+name+'.log')).read_text()
 assert 'reason=verified 120 original demo frames' in s
 rows={}
 rng={}
 for line in s.splitlines():
  v=line.split()
  if v[:1]==['[RNG_PRESENT]']:
   f=int(v[1]);assert v[2]=='1'
   rng[f]=(v[-2],v[-1])
  if v[:1]==['[PRESENT_MIX]']:
   a,b=map(int,v[1:3])
   if 0<=a<b<120:
    assert a+1==b and b not in rows
    rows[b]=(tuple(v[3:6]),int(v[6]))
 assert len(rows)==119 and rows.keys()<=rng.keys()
 return {f:(key,rng[f],t) for f,(key,t) in rows.items()}
for i in (1,2):
 a,b=[read(f'{arm}-{i}') for arm in ('base','retained')]
 for lo,hi in ((1,30),(31,119)):
  delta=[(a[f][2]-b[f][2])*1e-6 for f in range(lo,hi+1) if a[f][:2]==b[f][:2]]
  print(i,lo,hi,'matched',len(delta),'/',hi-lo+1,'host CPU ms saved mean/median', (mean(delta),median(delta)) if delta else None)
