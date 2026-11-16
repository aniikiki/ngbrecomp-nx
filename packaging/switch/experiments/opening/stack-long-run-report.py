"""Compare completed, seeded ABBA trials; do not align rows by FIFO origin."""
from pathlib import Path
from statistics import mean
import re
d=Path('build/switch-runtime/core-perf/opening-present-combined')
def read(arm,i):
    text=(d/f'stacklong-{arm}-{i}.log').read_text()
    assert 'reason=verified 120 original demo frames' in text
    rows=[(int(b),int(n),int(v),h,int(ns)) for b,n,v,h,ns in re.findall(
        r'^\[PRESENT_MIX\] \d+ (\d+) (\d+) (\d+) (\w+) (\d+) ',text,re.M)]
    assert len(rows)==120
    return rows,[int(re.search(rf'3D scene flips={f} draws=\d+ elapsed_ms=(\d+)',text)[1]) for f in (30,120)]
for i in (1,2):
    a,w=read('retained',i); b,v=read('stack-long-run',i)
    late=[(l[-1]-r[-1])/1e6 for l,r in zip(a,b) if l[1:4]==r[1:4] and 31<=l[0]<120 and 31<=r[0]<120]
    print(i,'wall ms (30/120) baseline/candidate',w,v,'full CPU ms saved',round(mean(l[-1]-r[-1] for l,r in zip(a,b))/1e6,4),
          'matched late rows',len(late),'matched late CPU ms saved',round(mean(late),4) if late else None)
