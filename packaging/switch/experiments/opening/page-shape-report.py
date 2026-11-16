from pathlib import Path
import re
s=Path('build/switch-runtime/core-perf/opening-page-shape/distribution.log').read_text()
assert 'verified 120 original demo frames' in s
r=[list(map(int,m.split())) for m in re.findall(r'^\[PAGE_SHAPE\] (.*)$',s,re.M)]
assert [(x[0],x[1]) for x in r]==[(f,i) for f in (30,120) for i in range(4)]
for f,n in ((30,30),(120,90)):
 group=[x[2:] for x in r if x[0]==f]
 for v in group:
  assert len(v)==16 and sum(v[:7])==v[15] and all(a<=b for a,b in zip(v[7:12],v[2:7])) and max(v[12:15])<=sum(v[2:7])
 v=list(map(sum,zip(*group)));total=sum(v[2:7]);assert total>0
 print('to flip',f,'all/frame',round(v[15]/n),'literal,slow,ordinary/frame',*[round(t/n) for t in (v[0],v[1],total)])
 print('ordinary widths 1/2/4/8/other %',*[round(100*t/total,2) for t in v[2:7]],'aligned %',round(100*sum(v[7:12])/total,2),'previous page %',round(100*v[12]/total,2),'ESP page %',round(100*v[13]/total,2))
