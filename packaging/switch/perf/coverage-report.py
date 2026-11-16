"""Counts, never an estimate of time saved or of safely removable draws."""
from collections import Counter
import sys
from pathlib import Path

groups = Counter()
frames = set()
for l in Path(sys.argv[1]).read_text().splitlines():
    if not l.startswith('[COVER] '):continue
    _,f,target,n,mask,zwrite,stencil,blend,q=l.split()
    frames.add(int(f))
    key=(int(target,16),int(mask),int(zwrite),int(stencil),int(blend))
    groups[key,int(q)!=0]+=1
if not frames:sys.exit('no completed queries')
zero=sum(v for (_,passing),v in groups.items() if not passing)
total=sum(groups.values())
print(f'{zero}/{total} completed sampled draws had zero passing samples ({zero/total:.1%}); {len(frames)} concurrent producer frames')
sizes=Counter()
for (key,_),v in groups.items():sizes[key]+=v
for k,n in sizes.most_common(10):
    z=groups[k,False]
    print(f'  rt={k[0]:08x} color={k[1]:x} depthWrite={k[2]} stencil={k[3]} blend={k[4]} : {z}/{n} zero')
