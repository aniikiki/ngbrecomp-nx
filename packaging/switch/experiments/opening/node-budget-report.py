from pathlib import Path
import re
s=Path('build/switch-runtime/core-perf/opening-node-budget/budget.log').read_text()
assert '[RESULT] status=1 reason=verified 120 original demo frames' in s
rows=[tuple(map(int,r.split())) for r in re.findall(r'^\[NODE_BUDGET\] ([0-9 ]+)$',s,re.M)]
assert [r[0] for r in rows]==[30,120]
for (end,queries,samples,ticks,controls,empty),frames in zip(rows,(30,90)):
    assert queries==238*frames and samples and controls
    print(end, 'searches',queries,'samples',samples,'controls',controls,
          'observed ns/search',round(ticks/samples,1),'empty ns',round(empty/controls,1),
          'adjusted host CPU ms/frame',round((ticks/samples-empty/controls)*queries/frames/1e6,4))
