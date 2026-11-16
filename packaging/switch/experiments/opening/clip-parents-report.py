"""Join actual 3078B0 loop boundaries to render verdicts; no forecast or skipping."""
from collections import Counter
from pathlib import Path
from struct import Struct
d=Path('build/switch-runtime/core-perf/opening-clip-parents')
log=(d/'joined.log').read_text()
assert 'original opening motion verified at 120' in log and 'reason=finished joined opening' in log
draw=list(Struct('<II').iter_unpack((d/'draw.bin').read_bytes()))
verdict=dict(draw)
prod=list(Struct('<9I').iter_unpack((d/'producer.bin').read_bytes()))
assert len(draw)==len(verdict) and set(verdict)=={i for i,_,_,_,n,*_ in prod if n}
tot=[Counter(),Counter()]
group=[]
seen={}
for seq,(i,f,key,pc,n,ns,index,count,base) in enumerate(prod,1):
    assert seq==i and n<=1
    if pc!=0x3079cc:
        assert not group
        continue
    assert index==len(group)
    if index==0: header=f,base,count
    assert header==(f,base,count)
    group.append((bool(n and verdict[i]&2),ns))
    if index+1<count:continue
    t=tot[int(f>30)]
    cut=sum(c for c,_ in group)
    t.update(groups=1,parts=count,culled=cut,whole=int(cut==count),mixed=int(0<cut<count),
             whole_parts=count if cut==count else 0,whole_ns=sum(ns for _,ns in group) if cut==count else 0)
    if count>1:
        t.update(multi=1,whole_multi=int(cut==count),whole_multi_parts=count if cut==count else 0)
    # Asset pointer + part count is available before the loop. Demonstrate
    # whether a visibility decision can be reused on that information alone.
    k=base,count
    if f<=30:seen[k]=seen.get(k,True) and cut==count
    elif seen.get(k,False):t.update(static_predictions=1,static_wrong=int(cut<count))
    group=[]
assert not group
for t,n in zip(tot,(30,90)):print(n,dict(t),'whole submits host ms/frame',round(t['whole_ns']/(1e6*n),4))
