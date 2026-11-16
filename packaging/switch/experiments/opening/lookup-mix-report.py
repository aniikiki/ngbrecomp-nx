"""Reconstruct actual bucket probes using the generated Switch table and observed keys."""
from pathlib import Path
import collections,re,sys
base=Path('build/switch-runtime')
src=(base/'gen/recomp_dispatch.c').read_text()
rows=[int(t,16) for t in re.findall(r'\{\s*0x([0-9A-Fa-f]+)u,\s*\(recomp_func_t\)',src)]
index=list(map(int,re.search(r'dispatch_index\[\] = \{(.*?)\};',src,re.S)[1].replace(',',' ').split()))
assert len(index)==32768 and len(rows)>10000
lo,span=[int(re.search('g_flat_'+k+r' = 0x([0-9A-Fa-f]+)u;',src)[1],16) for k in ('base','span')]
s=Path(sys.argv[1]).read_text();assert 'verified 120 original demo frames' in s
for f in (30,120):
 n,h,d=map(int,re.search(r'^\[LOOKUP_MIX\] '+str(f)+r' calls=(\d+) same_slot=(\d+) full=(\d+)$',s,re.M).groups())
 keys={int(k,16):int(v) for k,v in re.findall(r'^\[LOOKUP_KEY\] '+str(f)+r' (\w+) (\d+)$',s,re.M)}
 assert sum(keys.values())==n and not d
 probes=collections.Counter()
 for va,count in keys.items():
  cost=0
  if lo<=va<lo+span:
   j=((va*0x9e3779b1)&0xffffffff)>>17
   while True:
    cost+=1
    if not index[j] or rows[index[j]-1]==va:break
    j=(j+1)&32767
    assert cost<32768
  probes[cost]+=count
 print(f,'calls/frame',round(n/(30 if f==30 else 90),2),'keys',len(keys),'same_slot',round(h/n,4) if n else None,'probes',dict(sorted(probes.items())),'top',sorted(keys.items(),key=lambda x:-x[1])[:5])
