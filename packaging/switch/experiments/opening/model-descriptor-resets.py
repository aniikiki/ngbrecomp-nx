"""Bound how much is known about descriptor reuse at a model pipeline switch."""
from collections import Counter
from pathlib import Path
from struct import Struct

d = Path('build/switch-runtime/core-perf/opening-clip-siblings')
log = (d/'joined.log').read_text()
assert 'original opening motion verified at 120' in log and 'reason=finished joined opening' in log
frame = {i:f for i,f,*_ in Struct('<9I').iter_unpack((d/'producer.bin').read_bytes())}
assert set(frame.values()) == set(range(1,121))
rows = list(Struct('<14Q').iter_unpack((d/'bindings.bin').read_bytes()))
assert len(set(r[0] for r in rows)) == len(rows)
assert all(a[1]<b[1] for a,b in zip(rows,rows[1:]))
for lo, hi in [(1,30),(31,120)]:
    t = Counter()
    for a,b in zip(rows, rows[1:]):
        f = frame[b[0]]
        if not (lo <= f <= hi and frame[a[0]] == f and b[1] == a[1]+1): continue
        t['pairs'] += 1
        if a[5] == b[5]: continue
        t['pipeline_changes'] += 1
        # Views alone do not encode image layout. Do not count them.
        t['same_sampler'] += sum(x==y for x,y in zip(a[10:14], b[10:14]))
        t['same_constant_slot'] += (a[2]==b[2]) * sum(x==y for x,y in zip(a[3:5], b[3:5]))
    print(lo,hi,dict(t))
