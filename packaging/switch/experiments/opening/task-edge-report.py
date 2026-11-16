"""Resolve synthetic call-edge keys. Do not charge an inner named edge to its
outer edge a second time; key 0 is time outside all timed scopes."""
from pathlib import Path
from collections import defaultdict
import re
d=Path('build/switch-runtime/core-perf/opening-task-edges')
s=(d/'distribution.log').read_text()
assert '[RESULT] status=1 reason=verified 120 original demo frames' in s
edges={int(k,16):(p,t.split('_')[-1]) for k,p,t in (l.split() for l in (d/'host/edges.txt').read_text().splitlines())}
assert len(edges)==66
for f,n in ((30,30),(120,90)):
 rows=[(int(k,16),int(count),int(ns)) for k,count,ns in re.findall(rf'^\[CB_COST\] {f} (\w+) (\d+) (\d+)$',s,re.M)]
 assert len(rows)==len({r[0] for r in rows}) and rows
 print('frames',f-n+1,'..',f,'measured host thread ms/frame',round(sum(r[2] for r in rows)/n/1e6,3))
 byedge=defaultdict(lambda:[0,0])
 for k,count,ns in rows:
    if k not in edges:continue
    m=byedge[edges[k]];m[0]+=count;m[1]+=ns
 for path,(count,ns) in sorted(byedge.items(),key=lambda t:-t[1][1])[:12]:
    print(' -> '.join(path),count,'calls',round(ns/n/1e6,4),'ms/frame')
