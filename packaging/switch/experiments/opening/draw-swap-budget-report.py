"""Compare logical picture workload without comparing artificial-paced CPU to device CPU."""
from pathlib import Path
from statistics import median
import re
d=Path('build/switch-runtime/core-perf/opening-draw-correspondence')
for arm in ('normal','paced'):
 s=(d/f'swap-{arm}.log').read_text();assert 'verified 120 original demo frames' in s
 def rows(tag):return [tuple(map(int,v.split())) for v in re.findall(r'^\['+tag+r'\] ([0-9 ]+)$',s,re.M)]
 r=rows('GAME_SWAP_COST');w=rows('SWAP_SLICE');c=rows('DRAW_CADENCE')
 assert all(30<=a<=b<120 and min(h,cpu,e,p)>0 for a,b,h,cpu,e,p in r)
 assert all(b==v[0] for (_,b,*_),v in zip(r,r[1:]))
 assert len(r)+1==sum(n for f,n,k in w if 31<=f<=120)
 assert [f for f,n,k in c]==list(range(31,121)) and (sum(k for f,n,k in c)>0)==(arm=='paced')
 print(arm,'complete intervals',len(r))
 for label,vals in [('Draw',[x[2] for x in r]),('entries',[x[4] for x in r]),('polls',[x[5] for x in r])]:
  print(label,'min / median / max',min(vals),median(vals),max(vals))
