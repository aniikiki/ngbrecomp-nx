"""Compare whole intervals and ordinal geometry/RNG matches; never align on elapsed time."""
from pathlib import Path
import re, statistics as st,sys
d=Path('build/switch-runtime/core-perf/opening-rng-correspondence')
prefix=sys.argv[1] if len(sys.argv)>1 else 'paced-cumulative'
def read(name):
 s=(d/f'{prefix}-{name}.log').read_text()
 assert 'reason=verified 120 original demo frames' in s
 fifo=[list(map(int,m)) for m in re.findall(r'^\[OPEN_PAIR\] (\d+) \d+ (\d+) (\d+)$',s,re.M)]
 assert [r[0] for r in fifo]==list(range(1,121))
 sleeps=[list(map(int,m)) for m in re.findall(r'^\[DRAW_CADENCE\] (\d+) (\d+) (\d+)$',s,re.M)]
 if prefix=='paced-cumulative':assert [v[0] for v in sleeps]==list(range(31,121)) and sum(x[2] for x in sleeps)>0
 rng=None;rows=[]
 for line in s.splitlines():
  x=line.split()
  if not x:continue
  if x[0]=='[RNG_PRESENT]':rng=x[1:]
  if x[0]=='[PRESENT_MIX]':
   assert rng and int(rng[0])==int(x[2]) and int(rng[1])==1
   rows.append((int(x[1]),int(x[2]),tuple(x[3:6]+rng[-2:]),int(x[6])/1e6));rng=None
 w=int(re.search(r'3D scene flips=120 draws=\d+ elapsed_ms=(\d+)',s)[1])
 return fifo,[x for x in rows if x[0]>=30 and x[1]<120],w,sum(x[2] for x in sleeps)
for i in (1,2):
 a,x,t,ns=read(f'original-{i}');b,y,u,ms=read(f'split-{i}')
 saved=[(l[1]-r[1])/1e6 for l,r in zip(a,b)]
 match=[l[3]-r[3] for l,r in zip(x,y) if l[2]==r[2]]
 print(i,'sleeps orig/candidate',ns,ms,'FIFO cpu ms saved early/late/all',*[round(st.mean(v),4) for v in (saved[:30],saved[30:],saved)],'120 flip wall ms saved',t-u,'late Present counts',len(x),len(y),'ordinal dual matches',len(match),'matched CPU saving',round(st.mean(match),4) if match else None)
