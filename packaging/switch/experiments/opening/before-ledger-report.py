"""Use independent per-hook empty controls; rank replicated estimates, not call counts."""
from pathlib import Path
import re
root=Path('build/switch-runtime/core-perf/opening-rng-correspondence')
names={int(i):n for n,i in re.findall(r'D3DF_(\w+) = (\d+)',Path('src/d3d/d3d_funcs.h').read_text())}
runs=[]
for i in (1,2):
 s=(root/f'before-ledger-{i}.log').read_text()
 assert 'reason=verified 120 original demo frames' in s
 rows={}
 for f,fn,c,n,ns,e,ens in re.findall(r'^\[BEFORE_COST\] (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)$',s,re.M):
  f,fn,c,n,ns,e,ens=map(int,(f,fn,c,n,ns,e,ens))
  assert f in (30,120) and (f,fn) not in rows
  rows[f,fn]=(n,e,(ns/n-ens/e)*c/(30 if f==30 else 90)/1e6 if n and e else None)
 runs.append(rows)
for f in (30,120):
 eligible=[fn for window,fn in runs[0] if window==f and all(min(r.get((f,fn),(0,0,None))[:2])>=20 for r in runs)]
 print('through',f,'eligible (20+ real and control in each run)',len(eligible))
 for fn in sorted(eligible,key=lambda fn:-min(r[f,fn][2] for r in runs))[:10]:
  print(names[fn],*[round(r[f,fn][2],5) for r in runs])
