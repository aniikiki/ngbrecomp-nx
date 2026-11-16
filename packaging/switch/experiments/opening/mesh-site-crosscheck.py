"""Join an independent opening call-site census to timed sites, without charging parent scopes."""
from pathlib import Path
from collections import Counter
import re
d=Path('build/switch-runtime')
old=(d/'core-perf/opening-mesh-cost/budget.log').read_text()
new=(d/'core-perf/opening-guest-sites/budget.log').read_text()
assert all('verified 120 original demo frames' in s for s in (new,old))
body=(d/'gen/recomp_0028.c').read_text().split('void sub_0030BCA0(void)\n{')[1].split('\n}')[0]
sites=re.findall(r'PUSH32\(esp, 0x(\w+)u\); RECOMP_(?:ABI_CALL\(0x(\w+)u|ICALL_SAFE_AT\()',body)
assert len(sites)==18
for f,nframes in ((30,30),(120,90)):
    count={(int(ret,16),int(va,16)):int(n) for ret,va,n in re.findall(r'^\[GUEST_SITE\] '+str(f)+r' (\w+) (\w+) (\d+)$',new,re.M)}
    rank=[]
    for i,c,n,t,b,z,x in re.findall(r'^\[TREE_COST\] '+str(f)+r' (\d+) calls=(\d+) samples=(\d+) ns=(\d+) blanks=(\d+) blank_ns=(\d+) cross=(\d+)$',old,re.M):
        i,c,n,t,b,z,x=map(int,(i,c,n,t,b,z,x))
        ret,va=sites[i]
        if not (va and n and b and not x):continue
        tpc=(t/n-z/b)/1000
        newer=count.get((int(ret,16),int(va,16)),0)
        rank.append((tpc*c/(1000*nframes),ret,va,c,newer,tpc))
    print('phase',f,'top independently timed direct sites; calls from distinct trials')
    for cost,ret,va,c,newer,tpc in sorted(rank,reverse=True)[:6]:
        print(ret,va,c,newer,round(tpc,3),'us/call',round(cost,4),'measured ms/frame')
