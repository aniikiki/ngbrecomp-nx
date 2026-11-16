from pathlib import Path
from collections import Counter
import re
s=Path('build/switch-runtime/core-perf/opening-mesh-recipe-census/fields-budget.log').read_text()
assert 'verified 120 original demo frames' in s
nrs=166;ntss=32
for r,j,n in re.findall(r'^\[RECIPE_FIELD\] (\d+) (\d+) (\d+)$',s,re.M):
    j=int(j);name=f'rs[{j}]' if j<nrs else f'tss[{(j-nrs)//ntss}][{(j-nrs)%ntss}]' if j<nrs+4*ntss else f'simple method 0x{4*(j-nrs-4*ntss):04x}'
    print('training',r,name,n)
rows=[tuple(map(int,m.split())) for m in re.findall(r'^\[RECIPE_DETAIL\] (.*)$',s,re.M)]
assert rows[-1][0]==120 and all(len(r)==19 for r in rows)
a=rows[-1][1:]
checks=[tuple(map(int,m)) for m in re.findall(r'^\[MODEL_RECIPE\] (\d+) (\d+) (\d+)$',s,re.M)];assert len({f for f,k,n in checks})==120
late=Counter()
for f,k,n in checks:
    if f>30:late[k]+=n
assert sum(a)==sum(n for k,n in late.items() if k<64 and k&22==22)
print('all late',late.total(),'comparable geometry+bindings+material',sum(a))
for limit in (0,1,2,4,8,16):
    print('equal except frozen top',limit,'words:',sum(a[:limit+1]))
