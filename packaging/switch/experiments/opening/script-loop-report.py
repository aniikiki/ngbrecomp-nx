from pathlib import Path
import re
d=Path('build/switch-runtime/core-perf')
s=(d/'opening-script-loop-cost/budget.log').read_text()
old=(d/'opening-guest-sites/budget.log').read_text()
assert all('verified 120 original demo frames' in text for text in (s,old))
for f,frames in [(30,30),(120,90)]:
 rows=re.findall(r'^\[TREE_COST\] '+str(f)+r' (\d+) calls=(\d+) samples=(\d+) ns=(\d+) blanks=(\d+) blank_ns=(\d+) cross=(\d+)$',s,re.M)
 assert [int(r[0]) for r in rows]==[0,1]
 for row in rows:
    i,c,n,t,b,z,x=map(int,row)
    owner=('16270','16300')[i]
    independent=sum(map(int,re.findall(r'^\[GUEST_SITE\] '+str(f)+r' \w+ '+owner+r' (\d+)$',old,re.M)))
    assert c and n and b
    est=(t/n-z/b)*2*c/(frames*1000)
    print(f,owner,'chosen calls',c,'double / independent calls',2*c,independent,'samples',n,b,'cross',x,'estimated inclusive us/frame',round(est,2) if not x else None)
