"""Distinguish moving startup work from reducing total work; check actual adoption."""
from pathlib import Path
import re,sys
from statistics import mean
d=Path('build/switch-runtime/core-perf/opening-present-combined')
def read(arm,i):
 s=(d/f'{sys.argv[1]}-{arm}-{i}.log').read_text()
 assert 'reason=verified 120 original demo frames' in s
 prep=re.findall(r'^\[IDLE_DEVICE\] ready=1 elapsed_ns=(\d+)$',s,re.M)
 assert len(prep)==s.count('[IDLE_DEVICE] adopted at scene start')==int(arm=='prepared')
 cost=int(prep[0])/1e6 if prep else 0
 if prep:
  assert s.index('[IDLE_DEVICE] ready=1')<s.index('[IDLE_DEVICE] adopted at scene start')<s.index('3D scene flips=30 draws=')
 if prep and sys.argv[1]=='workerprep':
  work=re.findall(r'^\[IDLE_WORKER\] ready=1 work_ns=(\d+)$',s,re.M)
  join=re.findall(r'^\[IDLE_WORKER\] join_ns=(\d+)$',s,re.M)
  assert len(work)==len(join)==1
  assert s.index('[IDLE_WORKER] ready=1')<s.index('[IDLE_WORKER] join_ns=')<s.index('[IDLE_DEVICE] adopted at scene start')
  print('pair',i,'worker init ms',round(int(work[0])/1e6,3),'game thread join ms',round(int(join[0])/1e6,3))
 flips=re.findall(r'3D scene flips=(30|120) draws=(\d+) elapsed_ms=(\d+)',s)
 assert [int(v[0]) for v in flips]==[30,120]
 rows=[v for l in s.splitlines() if (v:=l.split())[:1]==['[PRESENT_MIX]'] and int(v[1])+1==int(v[2]) and 1<=int(v[2])<=119]
 assert [int(v[2]) for v in rows]==list(range(1,120))
 return cost,[int(v[2]) for v in flips],[(v[3:6],int(v[6])/1e6) for v in rows]
for i in (1,2):
 _,base,x=read('ordinary',i);cost,trial,y=read('prepared',i)
 matched=sum(a[0]==b[0] for a,b in zip(x,y))
 print('pair',i,'geometry matched',matched,'/119, title setup ms',round(cost,3),'wall saved first30/late90/all120 ms',base[0]-trial[0],base[1]-base[0]-trial[1]+trial[0],base[1]-trial[1], 'all120 saving minus moved setup ms',round(base[1]-trial[1]-cost,3),'late host game-thread ms/frame saved',round(mean(a[1]-b[1] for a,b in zip(x[30:],y[30:])),4))
