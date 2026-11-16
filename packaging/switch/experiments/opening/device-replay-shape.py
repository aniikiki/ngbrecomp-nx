"""Test frame correspondence before using host profiles to prioritize device work.
No conversion of host milliseconds to Tegra milliseconds. Only baseline logs.
"""
from pathlib import Path
from statistics import mean,median,correlation
import re
r=Path('build/switch-runtime')
hw,=list((r/'device-logs').glob('0.55.0-wide-*/boot.log'))
t=hw.read_text();assert re.findall(r'\[CLOCK\] first=\d+ cpu_hz=(\d+) gpu_hz=(\d+)',t)[:2]==[('1785000000','307200000')]*2
def read(rx,s):return [tuple(map(int,x)) for x in re.findall(rx,s,re.M)]
rows=read(r'\[DRAW_BOUND\] frame=(\d+) draws=(\d+) ticks=(\d+) cpu=(\d+) rc=0',t)
frames=list(range(31,121));assert [x[0] for x in rows]==frames
dc=[x[3]/19200 for x in rows];dd=[x[1] for x in rows]
runs=[]
for i in range(1,5):
 s=(r/'core-perf/wide-start'/f'paired-copy-default-original-{i}.log').read_text();assert 'verified 120 original demo frames' in s
 a=read(r'^\[OPEN_PAIR\] (\d+) \d+ (\d+) (\d+)$',s)
 b=read(r'^\[OPEN_WORK\] (\d+) (\d+) (\d+)$',s)
 assert [x[0] for x in a]==[x[0] for x in b]==list(range(1,121))
 runs.append([[c/1e6,d,e,p] for (_,c,d),(_,e,p) in zip(a[30:],b[30:])])
def delta(a):return [y-x for x,y in zip(a,a[1:])]
def stats(d,a):
 return ('%.3f'%correlation(d,a),'%.3f'%correlation(delta(d),delta(a)))
for i,k in enumerate(['CPU','draws','entries','polls']):
 x=[median(run[f][i] for run in runs) for f in range(90)]
 # Check repeatability on host first, using two disjoint pairs of runs.
 splits=[[mean(run[f][i] for run in pair) for f in range(90)] for pair in (runs[:2],runs[2:])]
 print(k,'host half-vs-half raw/delta',stats(*splits),'vs Switch CPU raw/delta',stats(dc,x))
 if i==1:print('vs Switch draws raw/delta',stats(dd,x),'per-frame |draw mismatch| median/max',median(abs(h-d) for h,d in zip(x,dd)),max(abs(h-d) for h,d in zip(x,dd)))
print('Switch draws vs Switch CPU raw/delta',stats(dd,dc))
# These four adjacent high/low slices are a sensitivity check, not exclusions
# from the FPS target. Test whether the remaining *typical* frames still run long.
burst={51,52,54,55}
for name,rs in [('all',rows),('four contrasting slices',[r for r in rows if r[0] in burst]),('remaining',[r for r in rows if r[0] not in burst])]:
 print(name,'n',len(rs),'mean game CPU',round(mean(r[3]/19200 for r in rs),3),'min CPU outside Draw mean',round(mean((r[3]-r[2])/19200 for r in rs),3))
sfile=r/'core-perf/opening-draw-correspondence/budget.log'
if sfile.exists() and 'verified 120 original demo frames' in (s:=sfile.read_text()):
 a=read(r'^\[DRAW_CORRESPOND\] (\d+) (\d+) (\d+)$',s)
 assert [x[0] for x in a]==list(range(1,121))
 a=a[30:];hs=[x[1] for x in a];ends=[x[2] for x in a]
 print('same host flip: HLE vs END equal',sum(x==y for x,y in zip(hs,ends)),'of 90, total',sum(hs),sum(ends))
 print('same counter, host vs Switch draws raw/delta',stats(dd,hs),'median |difference|',median(abs(x-y) for x,y in zip(dd,hs)))
 print('selected frame / Switch HLE / host HLE / host END',[(f,dd[f-31],hs[f-31],ends[f-31]) for f in sorted(burst)])
