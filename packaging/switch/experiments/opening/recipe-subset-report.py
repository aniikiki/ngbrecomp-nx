"""Compare the opening-only recipe list to the existing full recipe list."""
from pathlib import Path
from statistics import mean
import re
d=Path('build/switch-runtime/core-perf/opening-present-combined')
def read(kind,i):
 s=(d/f'recipesubset-warm-{kind}-{i}.log').read_text()
 assert 'verified 120 original demo frames' in s and '[IDLE_DEVICE] adopted at scene start' in s
 prep=int(re.search(r'\[IDLE_WORKER\] ready=1 work_ns=(\d+)',s)[1])/1e6
 totals=[tuple(map(int,m)) for m in re.findall(r'^\[OPEN_CREATES\] present=(\d+) shader=(\d+) pipeline=(\d+) us=(\d+)$',s,re.M)]
 assert [r[0] for r in totals]==[1,30,120]
 rows=[(int(n),int(v),h,int(b),int(ns)) for a,b,n,v,h,ns in re.findall(r'^\[PRESENT_MIX\] (\d+) (\d+) (\d+) (\d+) (\w+) (\d+) ',s,re.M)]
 wall=[int(re.search(rf'3D scene flips={f} draws=\d+ elapsed_ms=(\d+)',s)[1]) for f in (30,120)]
 return prep,totals,rows,wall
for i in (1,2):
 a,c,r,w=read('full',i);b,e,t,v=read('small',i)
 assert len(r)==len(t)>110
 late=[(x[-1]-y[-1])/1e6 for x,y in zip(r,t) if x[:3]==y[:3] and 31<=x[3]<120 and 31<=y[3]<120]
 print(i,'full/small prep ms',round(a,2),round(b,2),'full/small wall at flip 30/120',w,v,'cumulative first-use [Present,shader,pipe,microseconds]',c,e,'matching geometry',sum(x[:3]==y[:3] for x,y in zip(r,t)),len(r),'late CPU delta ms',round(mean(late),4) if late else None)
