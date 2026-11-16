"""Select guest body names on two retained runs; count exclusive hits on two held-out runs."""
from pathlib import Path
import re,runpy
from collections import Counter
p=Path(__file__).parent
d=Path('build/switch-runtime/core-perf')
analyze=runpy.run_path(str(p/'copy-profile-rank.py'))['analyze']
# Device is a different build. Normalize only directly named generated functions.
def key(n):
    m=re.fullmatch(r'(?:ngb_reg_)?((?:sub_|d3d_orig_)[0-9A-Fa-f]+)(?:\.localalias)?',n)
    return m[1] if m else None
device=[x.split('\t') for x in (d/'opening-setup/leaf-budget.tsv').read_text().splitlines() if '\t' in x]
for lo,hi in ((1,30),(31,120)):
    (a,b),total=analyze(d/'opening-copy-profile')[lo]
    rows=[x for x in device if lo<=int(x[0])<=hi and int(x[1])==1]
    dev=Counter(key(x[3]) for x in rows)
    for count in (1,5,10,25,50):
        select=sorted(a,key=lambda s:(-a[s],s))[:count]
        obs=sum(b[s] for s in select)
        hits=sum(dev[key(s)] for s in select)
        print(lo,hi,count,'heldout',obs,total[1],'device',hits,len(rows))
