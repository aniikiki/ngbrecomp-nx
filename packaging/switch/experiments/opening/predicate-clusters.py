"""Classify saved device stacks into verified game tasks, using the innermost callback.
Report sampled program locations, not a removable CPU-time estimate."""
from pathlib import Path
from collections import Counter
import re,json,runpy
base=Path('build/switch-runtime');rel=base/'history/0.51.0-rc1'
api=runpy.run_path(str(Path(__file__).resolve().parents[2]/'analyze-profile.py'))
s=api['load_symbols'](rel/'symbols.gz')
w=api['parse_windows']((base/json.loads((rel/'deployment.json').read_text())['hardware_log']).read_text().splitlines())[1,120]
tasks=Counter();branches=Counter()
for f,_,_,_,_,pcs in w['profiles']['guest'][1]:
 if not 2<=f<=120:continue
 st=[s(pc).removeprefix('ngb_reg_').split('.localalias')[0] for pc in pcs]
 try:i=st.index('sub_0030C8B0')
 except ValueError:tasks['unresolved']+=1;continue
 above=[v for v in reversed(st[:i]) if v.startswith('sub_')]
 key=above[0] if above else 'unresolved';tasks[key]+=1
 if key!='unresolved':
  branches[key,tuple(above[1:3])]+=1
print(tasks)
for (k,v),n in branches.most_common(15):print(k,n,v)
cost=Counter();bins=Counter()
for f,_,_,_,_,pcs in w['profiles']['guest'][1]:
 if not 2<=f<=120:continue
 st=[s(pc).removeprefix('ngb_reg_').split('.localalias')[0] for pc in pcs]
 if 'sub_001CA790' not in st:continue
 if any(v in {'execute_dma','service_dma','submit_dma','yield_worker','ngb_poll_due','poll_callbacks'} for v in st):k='service'
 elif any('WaitEm' in v or '__syscall_cond_wait' in v for v in st):k='wait'
 elif any('Recorded' in v for v in st):k='native recorder'
 elif any(v in {'d3d_hook','d3d_after','d3d_hle_call','d3d_hle_after'} for v in st):k='other graphics hook'
 elif any(v.startswith('d3d_orig_') for v in st):k='original Xbox D3D'
 else:k='remaining'
 cost[k]+=1
 if k=='remaining':bins[st[0]]+=1
print('1CA790 disjoint stacks',cost,'remaining leaves',bins.most_common(10))
