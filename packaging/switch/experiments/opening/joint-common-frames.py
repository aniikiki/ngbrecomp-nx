"""One late-Present cohort shared by both host pairs. Physical budgets are separate."""
from pathlib import Path
from statistics import mean,median
import re,sys
prefix="jointbuf" if "--buffered" in sys.argv else "joint"
d=Path('build/switch-runtime/core-perf/opening-present-combined')
def read(arm):
 s=(d/f'{prefix}-{arm}.log').read_text();assert 'reason=verified 120 original demo frames' in s
 v=[line.split() for line in s.splitlines() if line.startswith('[PRESENT_MIX] ')]
 assert len(v)==120
 return [(int(x[1]),int(x[2]),tuple(x[3:6]),int(x[6])/1e6,tuple(map(int,x[7:9]))) for x in v]
a,b,c,e=map(read,['base-1','next-1','base-2','next-2'])
rows=list(zip(a,b,c,e))
same=[r for r in rows if all(x[:3]==r[0][:3] for x in r) and 31<=r[0][1]<120 and r[0][1]==r[0][0]+1]
assert same
print('both pairs and all four signatures',len(same))
for ix in (0,2):
 old=[r[ix][3] for r in same];new=[r[ix+1][3] for r in same]
 print('pair',ix//2+1,'base/next CPU',mean(old),mean(new),'saved %',100*(1-sum(new)/sum(old)),
       'also equal entries/polls',sum(r[ix][4]==r[ix+1][4] for r in same))
both=[r for r in same if all(r[ix][3]>r[ix+1][3] for ix in (0,2))]
print('faster in both pairs',len(both),'of',len(same))
for j in (31,61,91):
 ss=[r for r in same if j<=r[0][1]<j+30]
 if ss:print('phase',j,len(ss),'mean saving',*[round(mean(r[i][3]-r[i+1][3] for r in ss),3) for i in (0,2)])
s=next(Path('build/switch-runtime/device-logs').glob('0.55.0-wide-*/boot.log')).read_text()
w=[(int(f),int(t)) for f,t in re.findall(r'3D scene flips=(30|120) draws=\d+ elapsed_ms=(\d+)',s)[:2]]
assert [f for f,_ in w]==[30,120]
for label,ms,n in [('early',w[0][1],30),('late',w[1][1]-w[0][1],90),('all',w[1][1],120)]:
 print('baseline Switch wall',label,ms,'required reduction %',round(100*(1-n*1000/60/ms),2))
