"""Estimate ordinary repeatability from already completed paired-copy reference runs.
The four original runs execute the same code within each tag. Contrast outer vs inner
runs to balance a linear drift; recorded intervals include workload variation."""
from pathlib import Path
import re,statistics as st,itertools
p=Path(__file__).parent;d=Path('build/switch-runtime/core-perf/wide-start')
line=next(l for l in (p/'run-page-limit.sh').read_text().splitlines() if l.startswith('if [ "$tag" = row-range ]'))
tags=re.findall(r'\[ "\$tag" = ([\w-]+) \]',line)
def read(f):
 s=f.read_text();assert 'verified 120 original demo frames' in s
 v=[(int(k),int(t)/1e6,int(w)) for k,t,w in re.findall(r'^\[OPEN_PAIR\] (\d+) \d+ (\d+) (\d+)$',s,re.M)]
 assert [x[0] for x in v]==list(range(1,121))
 return v
runs={}
for t in tags:
 logs=[d/f'{t}-original-{j}.log' for j in range(1,5)]
 if all(f.exists() for f in logs):runs[t]=list(map(read,logs))
print('independent experiment blocks',len(runs),'reference runs',len(runs)*4)
for lo in (0,30):
 delta={t:sum(sign*st.mean(v[1] for v in run[lo:])/2 for sign,run in zip([1,-1,-1,1],rs)) for t,rs in runs.items()}
 print('frames',lo+1,'..120: within-block same-code 2 vs 2, median / 90th percentile absolute ms:',round(st.median(map(abs,delta.values())),4),round(st.quantiles(list(map(abs,delta.values())),n=10,method='inclusive')[8],4))
 # Two independent blocks constitute a four-vs-four descriptive sensitivity check.
 a=[abs((x+s*y)/2) for x,y in itertools.combinations(delta.values(),2) for s in (-1,1)]
 print('balanced 4 vs 4 descriptive median / 90th percentile abs ms:',round(st.median(a),4),round(st.quantiles(a,n=10,method='inclusive')[8],4))
