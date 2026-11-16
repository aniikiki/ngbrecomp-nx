"""Join every command to its producer scope; unknown or missing commands never count."""
from collections import Counter
from pathlib import Path
from struct import iter_unpack
import sys
base=Path(sys.argv[1])
rows=list(iter_unpack("<5I",(base/"mesh-cost.bin").read_bytes()))
draws=Counter()
for mesh,cut in iter_unpack("<2I",(base/"mesh-draw.bin").read_bytes()):
    assert cut<=1
    draws[mesh,cut]+=1
if not rows or set(r[1] for r in rows)!=set(range(1801,1921)):sys.exit("incomplete producer trace")
counts=Counter(); times=Counter()
for mesh,frame,key,cmd,ns in rows:
    yes,no=draws[mesh,1],draws[mesh,0]
    k="unmatched" if yes+no!=cmd else "no draws" if not cmd else "entirely outside" if yes==cmd else "mixed" if yes else "other"
    counts[k]+=1;times[k]+=ns
print(f"{len(rows)} model submissions, {sum(draws.values())} renderer draws across 120 scene frames")
for k in counts:
    print(f"{k}: {counts[k]} submissions; {times[k]/120e6:.4f} ms per game frame")
if counts["unmatched"]:
    raise SystemExit("missing draw classifications; do not infer full-scope costs")
