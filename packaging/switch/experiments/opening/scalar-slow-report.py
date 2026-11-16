"""Summarize the external scalar fallback only. Short intervals can be below timer noise."""
from pathlib import Path
import re,sys
s=Path(sys.argv[1]).read_text();assert 'verified 120 original demo frames' in s
rows=[tuple(map(int,r)) for r in re.findall(r'^\[SCALAR_SLOW\] (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)$',s,re.M)]
assert [(r[0],r[1]) for r in rows]==[(f,i) for f in (30,120) for i in range(6)]
for f,i,n,k,t,b,e,x in rows:
 if not n:continue
 period=30 if f==30 else 90
 print(f,i,'calls/frame',round(n/period,2),'samples',k,b,'cross',x,'observed/blank ns',round(t/k,2) if k else None,round(e/b,2) if b else None,'corrected ms/frame',round((t/k-e/b)*n/period/1e6,5) if k and b and not x else None)
