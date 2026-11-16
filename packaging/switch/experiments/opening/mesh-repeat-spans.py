"""Potential reusable model sequences from the *immediately preceding* frame. No draws skipped."""
from pathlib import Path
from collections import Counter,defaultdict
from struct import Struct
root=Path('build/switch-runtime/core-perf')
def compare(frames,mask):
    prev=[];tot=Counter()
    for frame,items in enumerate(frames,1):
        # (caller,part) or exact caller,part and selected input matrices.
        keys=[(pc,key,*(m[i:i+64] for i in mask)) if n else None for _,key,pc,n,ns,m in items]
        pos=defaultdict(list)
        for j,x in enumerate(prev):
            if x is not None:pos[x].append(j)
        starts=hits=longhits=cost=0;i=0
        while i<len(keys):
            best=0
            for j in pos.get(keys[i],()):
                k=1
                while i+k<len(keys) and j+k<len(prev) and keys[i+k] is not None and keys[i+k]==prev[j+k]:k+=1
                best=max(best,k)
            if best:starts+=1;hits+=best
            if best>=8:longhits+=best;cost+=sum(it[4] for it in items[i:i+best])
            i+=max(1,best)
        if frame>30:tot.update(rows=len(items),spans=starts,hits=hits,longhits=longhits,ns=cost,total_ns=sum(it[4] for it in items))
        prev=keys
    return tot
for tag in ('opening-clip-join','opening-clip-early'):
    d=root/tag;s=(d/'joined.log').read_text()
    assert '[JOIN] original opening motion verified at 120' in s and 'reason=finished joined opening' in s
    frames=[[] for _ in range(120)]
    for seq,frame,key,pc,n,ns,mat in Struct('<6I192s').iter_unpack((d/'producer.bin').read_bytes()):
        assert 1<=frame<=120 and n<=1
        frames[frame-1].append((seq,key,pc,n,ns,mat))
    assert all(frames) and [x[0] for fr in frames for x in fr]==list(range(1,1+sum(map(len,frames))))
    for name,mask in [('identity',()),('world',(0,)),('view/projection',(64,128)),('all',(0,64,128))]:
        t=compare(frames,mask);print(tag,name,t['longhits'], '/',t['rows'],'calls in spans >=8; any',t['hits'],'spans',t['spans'],'inclusive ms/frame covered',round(t['ns']/90e6,3),'of',round(t['total_ns']/90e6,3))
