"""Gate cumulative replay on matched geometry/RNG, repeat CPU wins and no pooled wall regression."""
from pathlib import Path
from statistics import mean
import re,sys
d=Path('build/switch-runtime/core-perf/opening-rng-correspondence')
def read(arm,i):
 s=(d/f'indexbatch-one-{arm}-{i}.log').read_text()
 assert 'reason=verified 120 original demo frames' in s
 r={}; rng={}; wall={}
 for l in s.splitlines():
  v=l.split()
  if v[:1]==['[PRESENT_MIX]'] and int(v[2])==int(v[1])+1 and 1<=int(v[2])<=119:
   k=int(v[2]);assert k not in r;r[k]=(v[3:6],int(v[6])/1e6)
  if v[:1]==['[RNG_PRESENT]'] and v[2]=='1':rng[int(v[1])]=v[-2:]
  m=re.fullmatch(r'\[SERVICE\] 3D scene flips=(30|120) draws=\d+ elapsed_ms=(\d+)',l)
  if m:wall[int(m[1])]=int(m[2])
 assert set(r)==set(range(1,120)) and r.keys()<=rng.keys() and wall.keys()=={30,120}
 return r,rng,wall
ok=True;wall_d=[]
for i in (1,2):
 a,r,w=read('cached',i);b,s,v=read('copied',i)
 matches=sum(a[k][0]==b[k][0] and r[k]==s[k] for k in a)
 saves=[mean(a[k][1]-b[k][1] for k in range(lo,120)) for lo in [1,31]]
 dw=(w[120]-v[120])/120; wall_d.append(dw)
 print('pair',i,'matched',matches,'CPU saved all/late',saves,'wall saved ms/frame',dw)
 ok=ok and matches==119 and min(saves)>0
ok=ok and mean(wall_d)>=0
print('cumulative replay warranted:',ok)
sys.exit(0 if ok else 1)
