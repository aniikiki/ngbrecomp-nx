"""Sampled CPU estimates corrected by independent empty-probe mean, not wall time."""
from pathlib import Path
import sys,re
s=Path(sys.argv[1]).read_text()
assert '[RESULT] status=1 reason=verified 120 original demo frames' in s
for end,frames in [(30,30),(120,90)]:
    rows=re.findall(rf'^\[SYNC_BUDGET\] end={end} calls=(\d+) section=(\d+) n=(\d+) ns=(\d+)$',s,re.M)
    vals={int(i):(int(c),int(n),int(ns)) for c,i,n,ns in rows}
    assert len(rows)==7 and set(vals)==set(range(7)) and len(set(c for c,n,ns in vals.values()))==1
    empty=vals[6][2]/vals[6][1]
    for i,name in enumerate(('render states','simple methods','texture stages','shader constants','matrices/material','whole sync')):
        calls,n,ns=vals[i]
        print(end,name,'samples',n,'estimated ms/frame',round((ns/n-empty)*calls/frames/1e6,5))
