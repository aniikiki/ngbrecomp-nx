"""Split recorder waits using same-run measurements; never extrapolate to NVK."""
import re
from pathlib import Path
s=Path('build/switch-runtime/core-perf/opening-wait-origin/budget.log').read_text()
assert 'reason=verified 120 original demo frames' in s
rows=[tuple(map(int,m)) for m in re.findall(r'^\[WAIT_ORIGIN\] (\d+) (\d+) (\d+) (\d+) (\d+)$',s,re.M)]
assert [(f,k) for f,k,*_ in rows]==[(f,k) for f in (1,2,3,4,30,120) for k in (0,1)]
for lo,hi in ((1,1),(2,2),(3,30),(31,120)):
 print('frames',lo,hi)
 for kind in (0,1):
  r=[v for v in rows if lo<=v[0]<=hi and v[1]==kind]
  n,b,t=map(sum,zip(*(v[2:] for v in r)))
  assert b<=n
  print(('previous present','drain')[kind],n,b,round(t/1e6,3),'ms total')
