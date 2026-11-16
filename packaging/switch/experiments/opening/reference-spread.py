"""Measure repeated reference run spread, never mix baselines across sessions."""
from itertools import combinations
from pathlib import Path
import re
from statistics import mean,median
root=Path('build/switch-runtime/core-perf/wide-start')
# All of these explicitly select paired-copy as original; pair within block.
tags=('row-range','matrix-four','size-hot','cold-scalar','light-before','light-before-confirm','literal-xmm')
def read(tag,i):
    s=(root/f'{tag}-original-{i}.log').read_text()
    assert 'reason=verified 120 original demo frames' in s
    rows=[tuple(map(int,m)) for m in re.findall(r'^\[OPEN_PAIR\] (\d+) \d+ (\d+) (\d+)$',s,re.M)]
    assert [r[0] for r in rows]==list(range(1,121))
    return rows
for start in (1,31):
    spans=[];split=[]
    for tag in tags:
        refs=[mean(r[1] for r in read(tag,i)[start-1:])/1e6 for i in range(1,5)]
        spans.extend(abs(x-y) for x,y in combinations(refs,2))
        # Chronological inner vs outer reference runs; no candidate measurements.
        split.append(abs((refs[0]+refs[3]-refs[1]-refs[2])/2))
    print(start,'within-block absolute pair differences',len(spans),'median',median(spans),
          'reference outer-vs-inner splits',len(split),'median',median(split),'range',min(split),max(split))
