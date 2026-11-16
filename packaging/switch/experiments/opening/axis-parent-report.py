"""Estimate child work using inclusion probability; do not add children to their parent."""
from pathlib import Path
import re,sys
s=Path(sys.argv[1]).read_text();assert 'verified 120 original demo frames' in s
rows=[tuple(map(int,r)) for r in re.findall(r'^\[AXIS_PARENT\] (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)$',s,re.M)]
assert [(f,i) for f,i,*_ in rows]==[(f,i) for f in (30,120) for i in range(13)]
names=['parent','3059A0@ED65','3066B0@ED6A','13F960@EE1E','13F960@EE60','1C260@EEA3','1C260@EEBC','144160@EED5','13F960@EF4A','140590@EFDF','144210@F0DE','303DA0@F304','3059A0@F31D']
for end in (30,120):
 a=[r for r in rows if r[0]==end];period=30 if end==30 else 90
 total=0;missing=0
 for f,i,n,k,t,b,e,cross in a:
  if not n:continue
  if not k or not b or cross:
   missing+=1;print(f,i,'no estimate',n,k,b,cross);continue
  estimate=n*(t/k-e/b)/1e6/period*(32/31 if i else 1)
  print(f,names[i],n,k,round(estimate,5))
  if i:total+=estimate
  else:parent=estimate
 print(f,'child sum',round(total,5),'residual incl unmeasured & probe overhead',round(parent-total,5),'missing',missing)
