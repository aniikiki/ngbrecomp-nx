from itertools import combinations
from pathlib import Path
import re
d=Path('build/switch-runtime/core-perf/opening-present-combined')
px={}
for name in ('control-1','joined-1','joined-2','control-2'):
 s=(d/f'strip-cross-{name}.log').read_text()
 assert 'reason=verified 120 original demo frames' in s
 r=re.findall(r'^\[OPEN_PIXELS\] (\d+) (\w+)$',s,re.M)
 assert [int(i) for i,_ in r]==list(range(120))
 m=[int(v) for v in re.findall(r'strips_merged=(\d+)',s)]
 assert len(m)>=2 and (m[1]>0)==name.startswith('joined')
 px[name]=[v for _,v in r]
 print(name,'merged by 120',m[1])
for a,b in combinations(px,2):
 print(a,b,'exact matching full frames',sum(x==y for x,y in zip(px[a],px[b])))
rep=[i+1 for i,(a,b,c,e) in enumerate(zip(*px.values())) if a==e and b==c and a!=b]
print('repeatable setting-specific differences (1-based)',rep)
