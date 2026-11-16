"""Use independent empty-clock samples. Estimates are host CPU, not Switch timings."""
from pathlib import Path
from collections import defaultdict
from bisect import bisect_right
import sys
d=Path('build/switch-runtime/core-perf/opening-target-memory')
symbols=sorted((int(line.split()[0],16),line.split()[1]) for line in (d/'text.txt').read_text().splitlines())
addr=[s[0] for s in symbols]
ops=['memcmp','memcpy','memmove','memset']
for fn in sys.argv[1:] or ['run-1.log','run-2.log']:
 text=(d/fn).read_text();assert 'reason=verified 120 original demo frames' in text
 for end,frames in [(30,30),(120,90)]:
  totals=defaultdict(lambda:[0]*6);rank=[]
  for l in text.splitlines():
   w=l.split()
   if w[:2]!=['[TARGET_MEMORY]',str(end)]:continue
   op=int(w[2]);pc=int(w[3],16)-4
   row=list(map(int,w[4:]));calls,_,s,e,t,b=row
   totals[op]=[a+x for a,x in zip(totals[op],row)]
   if min(s,e)>=50:
    start,name=symbols[bisect_right(addr,pc)-1];ms=calls*(t/s-b/e)/frames/1e6
    rank.append((ms,ops[op],name+'+'+hex(pc-start),calls))
  assert totals
  print(fn,end)
  for op,row in sorted(totals.items()):
   calls,_,s,e,t,b=row
   print(ops[op],calls,'samples',s,e,'corrected ms/frame',round(calls*(t/s-b/e)/frames/1e6,5) if min(s,e) else None)
  print('largest sampled sites',sorted(rank,reverse=True)[:6])
