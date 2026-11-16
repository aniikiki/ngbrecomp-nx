"""Paired fixed-seed host results; no conversion to Switch time."""
import re
from pathlib import Path
from statistics import mean
d=Path('build/switch-runtime/core-perf/opening-present-combined')
def load(tag):
 s=(d/f'joint-{tag}.log').read_text()
 assert 'verified 120 original demo frames' in s
 walls=dict((int(f),int(t)) for f,t in re.findall(r'3D scene flips=(30|120) draws=\d+ elapsed_ms=(\d+)',s))
 rows=[(int(end), (draw,verts,h), int(cpu)/1e6) for end,draw,verts,h,cpu in re.findall(r'^\[PRESENT_MIX\] \d+ (\d+) (\d+) (\d+) (\w+) (\d+) ',s,re.M)]
 assert len(rows)==120 and set(walls)=={30,120}
 return walls,rows
for i in [1,2]:
 (w,a),(v,b)=[load(f'{tag}-{i}') for tag in ('base','next')]
 print('pair',i,'wall at 30/120',w,v,'full CPU ms/frame',round(mean(x[2] for x in a),4),round(mean(x[2] for x in b),4))
 late=[x[2]-y[2] for x,y in zip(a,b) if x[1]==y[1] and min(x[0],y[0])>=31 and max(x[0],y[0])<120]
 print('geometry matches',sum(x[1]==y[1] for x,y in zip(a,b)),'late matched intervals',len(late),'late matched CPU saved',round(mean(late),4) if late else None)
