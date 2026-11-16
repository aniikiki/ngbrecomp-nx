"""Rank estimated CPU in outer untaken wrappers, excluding samples with fiber switches."""
from pathlib import Path
import re
p=Path('build/switch-runtime/core-perf/opening-rng-correspondence')
names={int(i):n for n,i in re.findall(r'D3DF_(\w+) = (\d+)',Path('src/d3d/d3d_funcs.h').read_text())}
runs=[]
for i in (1,2):
 s=(p/f'xdk-body-ledger-{i}.log').read_text()
 assert 'reason=verified 120 original demo frames' in s
 rows={}
 for a in re.finditer(r'^\[XDK_BODY\] ([\d ]+)$',s,re.M):
  f,fn,c,n,t,e,u,sw=map(int,a[1].split())
  assert f in (30,120) and fn in names and (f,fn) not in rows
  rows[f,fn]=(n,e,sw,32*(t-n*u/e)/(30 if f==30 else 90)/1e6 if e else None)
 runs.append(rows)
for f in (30,120):
 keys=[k for k in runs[0] if k[0]==f and all(min(r.get(k,(0,0))[:2])>=20 for r in runs)]
 assert keys
 print('through',f,'eligible',len(keys),'switch-crossing samples excluded',*[sum(x[2] for k,x in r.items() if k[0]==f) for r in runs])
 for k in sorted(keys,key=lambda k:-min(r[k][3] for r in runs))[:10]:
  print(names[k[1]],*[round(r[k][3],4) for r in runs])
