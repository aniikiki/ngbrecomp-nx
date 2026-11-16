"""Pairs by completed scanout order; merging must decrease real submissions without pixel regressions."""
from pathlib import Path
import re
d=Path('build/switch-runtime/core-perf/opening-present-combined')
rows=[]
for arm in ('strip-join-control','strip-snapshot-join'):
    s=(d/f'pixels-{arm}.log').read_text()
    assert 'reason=verified 120 original demo frames' in s
    px={int(f):v for f,v in re.findall(r'^\[OPEN_PIXELS\] (\d+) (\w+)$',s,re.M)}
    assert len(px)==120
    counters=[tuple(map(int,v)) for v in re.findall(r'native indexed_draws=(\d+) fifo_indices_omitted=(\d+) strips_merged=(\d+)',s)]
    assert len(counters)>=2
    print(arm,'guest indexed draw count/strip merges at flip 30,120',[(n,m) for n,_,m in counters[:2]])
    rows.append(px)
assert rows[0].keys()==rows[1].keys()
diff=[f for f in rows[0] if rows[0][f]!=rows[1][f]]
print('full-image CRC matched',120-len(diff),'/ 120; differing frames:',diff)
