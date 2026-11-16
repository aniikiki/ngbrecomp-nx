"""One instrumented access distribution; counts are not CPU times."""
import re
from pathlib import Path
s=Path('build/switch-runtime/core-perf/opening-memory-census/distribution.log').read_text()
assert '[RESULT] status=1 reason=verified 120 original demo frames' in s
rows=[list(map(int,m.split())) for m in re.findall(r'^\[MEM_CENSUS\] (.*)$',s,re.M)]
assert [(x[0],x[1]) for x in rows]==[(f,i) for f in (30,120) for i in range(4)]
for end,n in [(30,30),(120,90)]:
 a=[x[2:] for x in rows if x[0]==end];counts=list(map(sum,zip(*a)))
 print('end',end,'scalar calls/frame',sum(counts)/n,'percent literal/image/nearSP/VM/low/alias/other',*[round(x*100/sum(counts),2) for x in counts])
 for u,r in zip((2,16,26,39),a):print(' unit',u,'calls/frame',round(sum(r)/n),'dynamic image/frame',round(r[1]/n),'nearSP/frame',round(r[2]/n))
