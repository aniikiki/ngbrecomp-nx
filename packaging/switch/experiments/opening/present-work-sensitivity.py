"""Report a predeclared workload sensitivity check alongside unfiltered paired CPU time.
Counters include timing-dependent services; filtering is descriptive, not a causal estimate.
"""
from pathlib import Path
from statistics import mean
import sys
directory,prefix,base,candidate=sys.argv[1:]
def rows(arm,run):
    text=(Path(directory)/f'{prefix}-{arm}-{run}.log').read_text()
    assert 'reason=verified 120 original demo frames' in text
    out={}
    for line in text.splitlines():
        v=line.split()
        if v[:1]!=['[PRESENT_MIX]']:continue
        i,j=map(int,v[1:3])
        if i+1==j and 1<=j<120:
            assert j not in out
            out[j]=(v[3:6],*map(int,v[6:9]))
    assert len(out)==119
    return out
for run in (1,2):
    a,b=rows(base,run),rows(candidate,run)
    for lo,hi in ((1,30),(31,119),(1,119)):
        ids=range(lo,hi+1)
        comparable=[k for k in ids if a[k][0]==b[k][0] and
                    all(abs(a[k][c]-b[k][c])*100<=max(a[k][c],b[k][c]) for c in (2,3))]
        def saved(keys):
            return round(mean((a[k][1]-b[k][1])/1e6 for k in keys),5) if keys else None
        print(run,lo,hi,'all',saved(ids),'similar work',len(comparable),'of',len(ids),saved(comparable))
