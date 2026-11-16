"""Paired screen-flip thread time; intervals include 1..120 exactly, startup separate."""
from pathlib import Path
from statistics import mean,median
import random,re,sys
runs=[]
for arg in sys.argv[1:]:
 s=Path(arg).read_text();assert 'verified 120 original demo frames: 0x00000078' in s
 r=[tuple(map(int,v)) for v in re.findall(r'^\[OPEN_PAIR\] (\d+) (\d+) (\d+) (\d+)$',s,re.M)]
 assert [v[0] for v in r]==list(range(1,121))
 runs.append(r)
for first,last in ((1,120),(3,120),(31,120)):
 pooled=[]
 for run in runs:
  rows=run[first-1:last];pairs=[sorted(rows[i:i+2],key=lambda v:v[1]) for i in range(0,len(rows),2)]
  assert all((a[1],b[1])==(0,1) for a,b in pairs)
  pooled.append([(a[2]-b[2])/1e6 for a,b in pairs])
  print(first,last,'base/alt CPU ms',*[round(mean(v[i][2] for v in pairs)/1e6,3) for i in (0,1)],'draws',*[round(mean(v[i][3] for v in pairs),1) for i in (0,1)])
 ds=[mean(v) for v in zip(*pooled)]
 blocks=[ds[i:i+4] for i in range(0,len(ds),4)]
 rng=random.Random(12345);boot=sorted(mean(sum(rng.choices(blocks,k=len(blocks)),[])) for _ in range(3000))
 print('matched savings',round(mean(ds),3),'median',round(median(ds),3),'block interval',round(boot[74],3),round(boot[2924],3))
