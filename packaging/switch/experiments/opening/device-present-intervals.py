"""Recover complete HLE Present intervals, preserving unresolvable multi-Present groups."""
import re,sys
from pathlib import Path
from itertools import accumulate

def recover(slices):
    # (FIFO frame, draws, presents, first and last completed draw counts).
    out=[];carry=0;prev=None
    for f,d,n,a,b in slices:
        assert 0<=a<=b<=d and n>=0
        if not n:
            assert a==b==0
            carry+=d
            continue
        if prev is not None:out.append((prev,f,1,carry+a))
        if n==1:assert a==b
        else:out.append((f,f,n-1,b-a))
        carry=d-b;prev=f
    return out

def device(path):
    s=Path(path).read_text()
    counts={int(f):int(n) for f,n in re.findall(r'\[OPEN_FLIP\] frame=(\d+) wall_ns=\d+ cpu_ticks=\d+ presents=(\d+) rc=0',s)}
    rows=[tuple(map(int,v)) for v in re.findall(r'\[DRAW_BOUND\] frame=(\d+) draws=(\d+) ticks=\d+ cpu=\d+ rc=0 first_draw=(\d+) last_draw=(\d+)',s)]
    if not rows:raise SystemExit('No first/last draw counts: this capture cannot reconstruct Present intervals')
    assert list(counts)==list(range(1,121)) and [f for f,*_ in rows]==list(range(31,121))
    return recover([(f,d,counts[f],a,b) for f,d,a,b in rows])

def check(arm):
    p=Path(f'build/switch-runtime/core-perf/opening-draw-correspondence/swap-{arm}.log')
    s=p.read_text();assert 'reason=verified 120 original demo frames' in s
    def rows(tag):return [tuple(map(int,m.split())) for m in re.findall(r'^\['+tag+r'\] ([0-9 ]+)$',s,re.M)]
    slices=[v for v in rows('SWAP_SLICE') if 31<=v[0]<=120]
    assert [f for f,n,d in slices]==list(range(31,121))
    ref=rows('GAME_SWAP_COST')
    # Prior FIFO number in GAME_SWAP_COST is zero-based relative to the slice end.
    frames=[f for f,n,d in slices for _ in range(n)]
    assert [(a+1,b+1) for a,b,*_ in ref]==list(zip(frames,frames[1:]))
    relative=list(accumulate((r[2] for r in ref),initial=0))
    starts={f:end-d for (f,n,d),end in zip(slices,accumulate(d for f,n,d in slices))}
    sizes={f:d for f,n,d in slices}
    lo=max(starts[f]-r for f,r in zip(frames,relative))
    hi=min(starts[f]+sizes[f]-r for f,r in zip(frames,relative))
    assert lo<=hi
    for offset in range(lo,hi+1):
        marks={f:[] for f,n,d in slices}
        for f,r in zip(frames,relative):marks[f].append(offset+r-starts[f])
        split=[(f,d,n,m[0] if m else 0,m[-1] if m else 0) for f,n,d in slices for m in [marks[f]]]
        groups=recover(split);j=0
        for a,b,n,d in groups:
            vs=ref[j:j+n];assert len(vs)==n and all((x[0]+1,x[1]+1)==(a,b) for x in vs)
            assert d==sum(x[2] for x in vs);j+=n
        assert j==len(ref)
    print(arm,'intervals',len(ref),'possible offsets',lo,hi,'zero/multiple Present slices',
          sum(n==0 for f,n,d in slices),sum(n>1 for f,n,d in slices))

if __name__=='__main__':
    if len(sys.argv)==2:
        for a,b,n,d in device(sys.argv[1]):print('FIFO',a,b,'intervals',n,'draws',d)
    else:
        for arm in ('normal','paced'):check(arm)
