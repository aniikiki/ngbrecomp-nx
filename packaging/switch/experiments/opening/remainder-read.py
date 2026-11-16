"""Decode first diagnostic session. Reject buckets which do not reconcile exactly."""
from pathlib import Path
from collections import defaultdict
import re,sys
s=Path(sys.argv[1]).read_text();m=re.search(r'\[RB_END\] total=(\d+) parent=(\d+) transitions=(\d+) overflow=(\d+)',s)
assert m and m[1]==m[2] and int(m[4])==0,'No reconciled 120-frame ledger'
s=s[:m.start()]; totals=defaultdict(int); prev=0; rows=re.findall(r'\[RB\] slot=(\d+) key=([a-fA-F0-9]+) ns=(\d+)',s)
summ=re.findall(r'\[RB_SUM\] slot=(\d+) sum=(\d+) parent_cum=(\d+)',s)
assert [int(x[0]) for x in summ]==list(range(7))
for g,ns,parent in summ:
 r=[(int(k,16),int(n)) for slot,k,n in rows if slot==g]
 assert len(set(k for k,n in r))==len(r) and sum(n for k,n in r)==int(ns)==int(parent)-prev
 prev=int(parent)
 if int(g)>=2:
  for k,n in r:totals[k]+=n
assert prev==int(m[1])
for k,n in sorted(totals.items(),key=lambda kv:-kv[1]):print(f'{k:08x}',f'{n/5e6:.3f}','ms/timed frame')
print('outside total',sum(totals.values())/5e6)
