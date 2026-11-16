"""Train part envelopes on one entire trace, then evaluate a frozen table on another."""
from pathlib import Path
from struct import Struct
from itertools import groupby
from collections import Counter
from math import isfinite
root=Path('build/switch-runtime/core-perf')
def trace(tag):
    d=root/('opening-clip-'+tag)
    log=(d/'joined.log').read_text()
    assert '[JOIN] original opening motion verified at 120' in log and 'reason=finished joined opening' in log
    prod=list(Struct('<6I192s').iter_unpack((d/'producer.bin').read_bytes()))
    rows=list(Struct('<2I192s16f6f').iter_unpack((d/'draw.bin').read_bytes()))
    draws={r[0]:r for r in rows}
    assert len(draws)==len(rows) and set(draws)=={r[0] for r in prod if r[4]}
    assert all(r[0]==i and r[4]<=1 for i,r in enumerate(prod,1))
    return d,prod,draws
_,train,draw=trace('join')
boxes={};reject=set()
for i,f,key,pc,n,*_ in train:
    k=(pc,key)
    if not n or not draw[i][1]&4:reject.add(k);continue
    b=draw[i][-6:]
    old=boxes.get(k,b)
    boxes[k]=tuple((min if j<3 else max)(old[j],b[j]) for j in range(6))
for k in reject:boxes.pop(k,None)
d,hold,draw=trace('early')
rows=list(Struct('<I16f').iter_unpack((d/'entry.bin').read_bytes()))
entry={r[0]:r[1:] for r in rows}
assert len(rows)==len(entry)==len(hold) and all(i in entry for i,*_ in hold)
def outside(b,m):
    if not all(map(isfinite,m)):return False
    tol=(1+sum(max(abs(b[j]),abs(b[j+3])) for j in range(3)))*max(map(abs,m))*2e-5+1e-4
    for j,s in ((0,1),(0,-1),(4,1),(4,-1)):
        c=[m[12+t]+s*m[j+t] for t in range(4)]
        if c[3]+sum(max(b[t]*c[t],b[t+3]*c[t]) for t in range(3)) < -tol:return True
    return False
print('frozen keys',len(boxes))
for lo,hi in ((1,30),(31,120)):
    stats=Counter();forecast=[]
    for i,f,key,pc,n,ns,_ in hold:
        if not lo<=f<=hi:continue
        # Only the frozen bounds and entry matrix inform this prediction.
        b=boxes.get((pc,key));yes=b is not None and outside(b,entry[i])
        stage=draw[i][1] if n else 0;cut=bool(stage&2)
        stats.update(submit=1,hit=b is not None,guesses=yes,missed=cut and not yes,false=yes and not cut,correct=yes and cut,ns=ns*(yes and cut))
        if b is not None:
            actual=draw[i][-6:] if stage&4 else None
            stats['ineligible']+=actual is None
            stats['bounds_escape']+=actual is not None and any(actual[j]<b[j] or actual[3+j]>b[3+j] for j in range(3))
        forecast.append((f,pc,yes and cut,ns))
    # Retrospective grouping only: caller and frame changes break spans; these
    # records do not contain parent instance identity or intervening non-model draws.
    runs=[list(g) for (f,pc,yes),g in groupby(forecast,lambda x:x[:3]) if yes]
    for n in (2,4,8):
        groups=[r for r in runs if len(r)>=n]
        print(lo,hi,'run >=',n,len(groups),sum(map(len,groups)),round(sum(x[3] for r in groups for x in r)/((hi-lo+1)*1e6),4),'host ms/frame in submits')
    print(lo,hi,dict(stats),round(stats['ns']/((hi-lo+1)*1e6),4),'host ms/frame all correct')
