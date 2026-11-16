"""Only calls completed before the corresponding model Draw, not inclusive CPU costs."""
from pathlib import Path
import re
s=Path('build/switch-runtime/core-perf/opening-mesh-recipe-census/setters-fields-budget.log').read_text()
assert 'verified 120 original demo frames' in s
top={int(j) for _,j in re.findall(r'^\[RECIPE_FIELD\] ([1-4]) (\d+) ',s,re.M)}
assert top=={294+x//4 for x in (0xa60,0xa64,0xa80,0xa84)}
hist=list(map(int,re.findall(r'^\[RECIPE_DETAIL\] 120 (.*)$',s,re.M)[-1].split()))
for g,expected in enumerate((sum(hist[:5]),sum(hist[5:]))):
 records=re.findall(r'^\[RECIPE_SETTERS\] '+str(g)+r' (.*)$',s,re.M)
 if not records:
    print(g,'no final snapshot');continue
 vals=list(map(int,records[-1].split()))
 rows,shader,stream,texture,other1,other2,other3,other4,material,ptr=vals
 assert rows==expected and stream==rows and ptr%4==0 and ptr<=4*material
 print(g,'rows',rows,'shader',shader,'stream',stream,'texture',texture,'other guarded',other1+other2+other3+other4,'material checks',material,'material forward copy path',ptr//4)
