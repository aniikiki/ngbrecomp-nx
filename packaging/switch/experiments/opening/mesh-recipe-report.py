"""Only selected recorded fields compare equal, not shader/texture contents or guest side effects."""
from pathlib import Path
from collections import Counter
import re
s=Path('build/switch-runtime/core-perf/opening-mesh-recipe-census/budget.log').read_text()
assert 'verified 120 original demo frames' in s
rows=[tuple(map(int,m)) for m in re.findall(r'^\[MODEL_RECIPE\] (\d+) (\d+) (\d+)$',s,re.M)]
assert set(f for f,k,n in rows)==set(range(1,121)) and all(0<=k<=64 and n>0 for f,k,n in rows)
for lo,hi in ((1,30),(31,120)):
    h=Counter()
    for f,k,n in rows:
        if lo<=f<=hi:h[k]+=n
    print(lo,hi,'total',h.total(),'previous-frame same occurrence',h.total()-h[64])
    for mask,name in ((1,'world'),(2,'geometry'),(4,'bindings'),(8,'render states'),(16,'material/lights'),(32,'view/projection'),(30,'geometry+bindings+states+material'),(31,'also world'),(63,'all measured')):
        print(name,sum(n for k,n in h.items() if k<64 and k&mask==mask))
