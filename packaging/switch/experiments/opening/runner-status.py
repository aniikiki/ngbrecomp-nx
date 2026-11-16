"""Only report completed opening windows. Never use software Vulkan FPS as a Switch estimate."""
from pathlib import Path
import re,statistics as st
d=Path('build/switch-runtime/core-perf/wide-start')
for tag in ('literals','ticket','register-ticket','compact','readonly','icall-direct','region-bias','hot-layout','stack-leaves','service-cost','fuse-hot','d3d-private','opening-speed','packed-ops','vector-registers'):
 runs={}
 for arm in ('original','limit'):
  for i in range(1,5):
   f=d/f'{tag}-{arm}-{i}.log'
   if not f.is_file():continue
   s=f.read_text()
   if '[RESULT] status=1 reason=verified 120 original demo frames' not in s:continue
   a=[tuple(map(int,r)) for r in re.findall(r'^\[OPEN_PAIR\] (\d+) \d+ (\d+) (\d+)$',s,re.M)]
   assert [r[0] for r in a]==list(range(1,121))
   runs[arm,i]=(st.mean(x[1] for x in a[30:])/1e6,sum(x[2] for x in a[30:]))
 pairs=[(runs['original',i],runs['limit',i]) for i in range(1,5) if ('original',i) in runs and ('limit',i) in runs]
 print(tag,len(runs),'/ 8 valid runs;',len(pairs),'pairs',[(round(a[0]-b[0],3),round(b[1]/a[1],3)) for a,b in pairs])
