"""Paired renderer-thread CPU and executed draw counts (offline combat only)."""
from pathlib import Path
from statistics import mean
import random
import sys

log = Path(sys.argv[1]).read_text()
if '[RESULT] status=1 reason=verified original combat window' not in log:
    raise SystemExit("combat did not complete")
rows = [tuple(map(int,l.split()[1:])) for l in log.splitlines() if l.startswith('[CUT] ')]
for lo,hi in ((1681,1800),(1801,1920)):
    by_id = {row[1]:row for row in rows if lo<=row[0]<=hi}
    pairs = []
    for i in sorted(by_id):
        if i%2 or i+1 not in by_id: continue
        a,b=sorted((by_id[i],by_id[i+1]),key=lambda x:x[2])
        assert a[2]==0 and b[2]==1 and a[6]==0
        pairs.append((a,b))
    if len(pairs)<40: raise SystemExit(f"incomplete window {lo}: {len(pairs)} pairs")
    times = [(a[3]-b[3])/1e6 for a,b in pairs]
    blocks = [times[n:n+4] for n in range(0,len(times),4)]
    rng = random.Random(47)
    boot = sorted(mean(sum(rng.choices(blocks,k=len(blocks)),[])) for _ in range(3000))
    print(f"{lo}..{hi}: {len(pairs)} pairs, renderer thread CPU (first draw to entry to Present):")
    for j in (0,1):
        us,req,drawn,cut = (mean(t[j][k] for t in pairs) for k in (3,4,5,6))
        print(f"  {'cut' if j else 'base'}: {us/1e6:.3f} ms; requested {req:.1f}, prepared {drawn:.1f}, skipped {cut:.1f}")
    print(f"  saved {mean(times):.3f} ms; 8-frame block interval [{boot[74]:.3f},{boot[2924]:.3f}]")
