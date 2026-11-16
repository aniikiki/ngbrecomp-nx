"""Time only the prefixes. The second has additional, non-shared work."""
from pathlib import Path
import re
s=Path('build/switch-runtime/core-perf/opening-actor-values/budget.log').read_text()
assert '[RESULT] status=1 reason=verified 120 original demo frames' in s
for end,frames in ((30,30),(120,90)):
 v=list(map(int,re.search(rf'^\[ACTOR_VALUES\] {end} (.+)$',s,re.M)[1].split()))
 assert len(v)==8 and v[1:3]==[0,0]
 print('window ending',end,'paired',v[0],'mismatches',v[3:])
 for side in (0,1):
  n,nsamp,ticks,nctrl,blank=map(int,re.search(rf'^\[ACTOR_PREFIX\] {end} {side} (.+)$',s,re.M)[1].split())
  assert n==v[0] and nsamp and nctrl
  print('pass',side,'samples/control',nsamp,nctrl,'raw/control ns',round(ticks/nsamp,2),round(blank/nctrl,2),'estimated prefix ms per host frame',round((ticks/nsamp-blank/nctrl)*n/frames/1e6,5))
