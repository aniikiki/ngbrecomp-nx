"""Classify lookup order. Increasing ranks alone do not authorize skipping links."""
import re
from pathlib import Path
from collections import Counter
s=Path('build/switch-runtime/core-perf/opening-node-order/budget.log').read_text()
assert 'reason=verified 120 original demo frames' in s
rows=re.findall(r'^\[NODE_ORDER\] (\d+) (\d+) (.+)$',s,re.M)
assert [int(f) for f,n,line in rows]==[1,30,31,60,90,120]
for f,n,line in rows:
    data=[(int(a,16),int(b,16),int(c),int(d,16)) for a,b,c,d in (x.split(':') for x in line.split())]
    assert len(data)==int(n)<=256
    prev={};adj=ascending=retained=0;pairs=Counter();keys=set()
    for i,(head,key,depth,node) in enumerate(data):
        if i and head==data[i-1][0]:adj+=1
        if head in prev:
            k,r,p=prev[head]
            if node and p and key>k and depth>r:
                ascending+=1;retained+=r
        prev[head]=key,depth,node;pairs[head,key]+=1;keys.add(head)
    print(f,'queries',n,'heads',len(keys),'repeat',sum(v-1 for v in pairs.values()),'same-head adjacent',adj,'key/rank both increasing',ascending,'prefix visits under unchanged-list assumption',retained,'total',sum(r for _,_,r,_ in data))
