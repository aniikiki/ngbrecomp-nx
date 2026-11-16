"""Group late pre-record CPU by same previous-frame input fields. No costs from a different run."""
from pathlib import Path
import re
s=Path('build/switch-runtime/core-perf/opening-mesh-recipe-census/clock-fields-budget.log').read_text()
assert 'verified 120 original demo frames' in s
hist=list(map(int,re.findall(r'^\[RECIPE_DETAIL\] 120 (.*)$',s,re.M)[-1].split()))
rows=re.findall(r'^\[MODEL_RECIPE\] (\d+) (\d+) (\d+)$',s,re.M)
total=sum(int(n) for f,_,n in rows if int(f)>30)
out=[]
for g,expected in enumerate((sum(hist[:5]),sum(hist[5:]),total-sum(hist))):
 a,n,ns=map(int,re.findall(r'^\[RECIPE_PRE\] '+str(g)+r' (\d+) (\d+) (\d+)$',s,re.M)[-1])
 assert a==expected and n>0
 out.append(a*ns/n/90e6);print(g,'draws',a,'samples',n,'us/sample',round(ns/n/1000,3),'pre-record CPU ms/host frame',round(out[-1],3))
print('total ms/frame',round(sum(out),3),'group 0 share',round(out[0]/sum(out),3))
