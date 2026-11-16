from pathlib import Path
from statistics import mean
import re
d=Path('build/switch-runtime/core-perf/opening-present-combined')
def read(arm):
 s=(d/f'recipeprep-{arm}.log').read_text()
 assert 'verified 120 original demo frames' in s
 assert s.index('[IDLE_DEVICE] ready=1')<s.index('[IDLE_DEVICE] adopted at scene start')
 windows=[int(re.search(rf'3D scene flips={f} draws=\d+ elapsed_ms=(\d+)',s)[1]) for f in (30,120)]
 join=int(re.search(r'\[IDLE_WORKER\] join_ns=(\d+)',s)[1])/1e6
 work=int(re.search(r'\[IDLE_WORKER\] ready=1 work_ns=(\d+)',s)[1])/1e6
 rows=[(int(a),int(b),int(n),int(v),h,int(ns)) for a,b,n,v,h,ns in re.findall(r'^\[PRESENT_MIX\] (\d+) (\d+) (\d+) (\d+) (\w+) (\d+) ',s,re.M)]
 return windows,join,work,rows
for i in (1,2):
 x,a,c,r=read(f'base-{i}');y,b,e,t=read(f'warm-{i}')
 assert len(r)==len(t) and len(r)>110
 late=[(l[5]-h[5])/1e6 for l,h in zip(r,t) if 31<=l[1]<120 and 31<=h[1]<120 and l[2:5]==h[2:5]]
 print(i,'base/warm first30 ms',x[0],y[0],'whole120 ms',x[1],y[1],'join ms',round(a,2),round(b,2),'background work ms',round(c,2),round(e,2),'same indexed geometry',sum(l[2:5]==h[2:5] for l,h in zip(r,t)),'/',(len(r),len(t)),'late matched CPU ms saved',round(mean(late),4) if late else None)
