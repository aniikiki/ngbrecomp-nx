"""Separate repeated query keys from traversal length; neither proves a valid cache."""
from pathlib import Path
import re
s=Path('build/switch-runtime/core-perf/opening-node-census/budget.log').read_text()
assert '[RESULT] status=1 reason=verified 120 original demo frames' in s
rows=[tuple(map(int,m.split())) for m in re.findall(r'^\[NODE_CENSUS\] ([0-9 ]+)$',s,re.M)]
assert [v[0] for v in rows]==[30,120]
for f,n,empty,repeated,nodes,steps,hits in rows:
    assert empty<=n and repeated<=n and hits<=n-empty and steps<=nodes and nodes>=n-empty
    print(f,'queries/empty/repeated/visits/links/hits',n,empty,repeated,nodes,steps,hits,
          'visits/query',round(nodes/n,2),'same-frame repeat fraction',round(repeated/n,4))
