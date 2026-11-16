"""Read both complete host experiments. Never interpret sequential batches as a randomized logging comparison."""
from pathlib import Path
import re,statistics as st
d=Path('build/switch-runtime/core-perf/opening-present-combined')
def load(prefix,arm):
 s=(d/f'{prefix}-{arm}.log').read_text()
 assert 'reason=verified 120 original demo frames' in s
 fifo=[x.split() for x in s.splitlines() if x.startswith('[OPEN_PAIR] ')]
 work=[x.split() for x in s.splitlines() if x.startswith('[OPEN_WORK] ')]
 assert [int(x[1]) for x in fifo]==[int(x[1]) for x in work]==list(range(1,121))
 v=[x.split() for x in s.splitlines() if x.startswith('[PRESENT_MIX] ')]
 assert len(v)==120
 if prefix=='jointbuf':assert s.index('[PRESENT_MIX]')>s.index('[WIDE] moving Vulkan scanouts=')
 return [((x[1:6]),int(x[6])/1e6) for x in v]
runs=[[load(prefix,arm) for arm in ('base-1','next-1','base-2','next-2')] for prefix in ('joint','jointbuf')]
for mode in ('within','across'):
 for i,r in enumerate(runs):
  cohort=[k for k in range(120) if 31<=int(r[0][k][0][1])<120 and int(r[0][k][0][0])+1==int(r[0][k][0][1]) and all(a[k][0]==r[0][k][0] for batch in (runs if mode=='across' else [r]) for a in batch)]
  if not cohort: print(mode,i,'empty');continue
  print(mode,i,'n',len(cohort),'CPU saved ms per interval',*[round(st.mean(r[j][k][1]-r[j+1][k][1] for k in cohort),4) for j in (0,2)])
