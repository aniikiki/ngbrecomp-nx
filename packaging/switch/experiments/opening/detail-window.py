"""Separate frames on which detailed timing actually runs. Compare with
nearby non-instrumented frames; independent replays are not identical work."""
from pathlib import Path
import re,statistics as st
d=Path('build/switch-runtime/core-perf/wide-start')
for i in range(1,5):
 rows=[]
 for arm in ('original','limit'):
  s=(d/f'detail-cost-{arm}-{i}.log').read_text()
  assert 'verified 120 original demo frames' in s
  on={f for f in range(1,121) if (f-1)%16==(((f-1)//16)*9)%16}
  counts=list(map(int,re.findall(r'scene sampled_frames=(\d+)',s)))
  assert counts[-1]==(len(on) if arm=='original' else 0)
  t={int(f):int(ns)/1e6 for f,ns in re.findall(r'^\[OPEN_PAIR\] (\d+) \d+ (\d+) \d+$',s,re.M)}
  assert sorted(t)==list(range(1,121));rows.append(t)
 diff={f:rows[0][f]-rows[1][f] for f in range(31,121)}
 treated=sorted(on&diff.keys())
 print(i,'detailed frames',treated,'mean savings ms',round(st.mean(diff[f] for f in treated),3),'ordinary',round(st.mean(v for f,v in diff.items() if f not in on),3))
