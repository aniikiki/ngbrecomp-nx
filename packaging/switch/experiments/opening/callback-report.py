"""Rank mutually exclusive per-target guest thread clocks; key 0 is outside
all wrapped dispatches. Counts are entries, including repeated same-target calls."""
from pathlib import Path
import re,sys
s=Path(sys.argv[1]).read_text()
assert '[RESULT] status=1 reason=verified 120 original demo frames' in s
for f,n in ((30,30),(120,90)):
 rows=[(int(k,16),int(count),int(ns)) for k,count,ns in re.findall(
     rf'^\[CB_COST\] {f} (\w+) (\d+) (\d+)$',s,re.M)]
 assert len(set(k for k,_,_ in rows))==len(rows) and rows and any(k==0 for k,_,_ in rows)
 total=sum(ns for _,_,ns in rows);outside=sum(ns for k,_,ns in rows if k==0)
 print(f'{f-n+1}..{f} measured thread: {total/n/1e6:.3f} ms/frame; outside {outside/n/1e6:.3f}; inside {(total-outside)/n/1e6:.3f}')
 for k,count,ns in sorted(rows,key=lambda r:-r[2])[:10]:
    print(f'{k:08x} {count:6d} {ns/n/1e6:.4f}')
