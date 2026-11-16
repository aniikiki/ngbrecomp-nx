"""Track work alongside 60 Hz plausibility. Mark crossed host thresholds only
when all windows are present. Never label an offline run a Switch result."""
from pathlib import Path
from statistics import mean
import sys,re
d=Path('build/switch-runtime/core-perf/wide-start')
tags=sys.argv[1:] or sorted({p.name[:-len('-original-1.log')] for p in d.glob('*-original-1.log')})
def read(p):
 if not p.exists():return
 s=p.read_text()
 if '[RESULT] status=1 reason=verified 120 original demo frames' not in s:return
 r=[tuple(map(int,v)) for v in re.findall(r'^\[OPEN_PAIR\] (\d+) \d+ (\d+) (\d+)$',s,re.M)]
 if [v[0] for v in r]!=list(range(1,121)):return
 return r
for tag in tags:
 pairs=[]
 for i in range(1,5):
  a=read(d/f'{tag}-original-{i}.log');b=read(d/f'{tag}-limit-{i}.log')
  if a and b:pairs.append((a,b))
 if len(pairs)!=4:continue
 print(tag,end=': ')
 for start in [0,30]:
  cpu=[1-sum(x[1] for x in b[start:])/sum(x[1] for x in a[start:]) for a,b in pairs]
  draws=[sum(x[2] for x in b[start:])/sum(x[2] for x in a[start:]) for a,b in pairs]
  print(f'{start+1}..120 host CPU {mean(cpu):+.1%} saved (pair range {min(cpu):+.1%}..{max(cpu):+.1%}), draw ratio {min(draws):.3f}..{max(draws):.3f}',end='; ')
 print()
