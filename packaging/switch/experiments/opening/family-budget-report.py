from pathlib import Path
import re
log=Path('build/switch-runtime/core-perf/opening-family-budget/budget.log').read_text()
assert 'verified 120 original demo frames' in log
rows=[list(map(int,x.split())) for x in re.findall(r'^\[FAMILY_BUDGET\] ([0-9 ]+)$',log,re.M)]
assert [(f,i) for f,i,*_ in rows]==[(f,i) for f in (30,120) for i in range(3)]
for end,frames in [(30,30),(120,90)]:
 totals=[]
 for f,i,c,n,t,b,z in rows:
  if f!=end:continue
  assert c==frames*[168,168,238][i] and min(n,b)>0
  totals.append(c/frames*(t/n-z/b)*1e-6)
 print(end,'per-body host ms/frame',*[round(x,5) for x in totals],'sum',round(sum(totals),5))
