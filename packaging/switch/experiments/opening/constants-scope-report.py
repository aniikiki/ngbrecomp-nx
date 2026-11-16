from pathlib import Path
import re
p=Path('build/switch-runtime/core-perf/opening-constants-scope/cost.log')
s=p.read_text()
assert 'reason=verified 120 original demo frames' in s
rows=[tuple(map(int,r.split())) for r in re.findall(r'^\[CS_COST\] ([\d ]+)$',s,re.M)]
assert [(f,a,b) for f,a,b,*_ in rows]==[(f,a,b) for f in (30,120) for a in range(2) for b in range(2)]
for f,a,b,k,n,t,m,z in rows:
 assert n>0 and m>0 and n+m<=k
 print(f,('deferred','constants')[a],('unchanged','changed')[b],k,n,m,round(k*(t/n-z/m)/(30 if f==30 else 90)/1e6,5),'ms/frame')
