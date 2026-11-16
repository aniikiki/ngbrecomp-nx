"""Compare old device and retained host exclusive generated-function samples by guest address."""
import bisect,re
from collections import Counter
from pathlib import Path
root=Path('build/switch-runtime/core-perf')
dev=Counter();host=Counter()
def add(c,fn):
 m=re.fullmatch(r'(?:ngb_reg_)?sub_([0-9A-Fa-f]+)',fn)
 if m:c[int(m[1],16)]+=1
for line in (root/'opening-setup/leaf-budget.tsv').read_text().splitlines():
 r=line.split('\t')
 if len(r)>4 and 31<=int(r[0])<=120:add(dev,r[3])
d=root/'opening-compact-profile';sy={}
for line in (d/'symbols.txt').read_text().splitlines():
 a,n,_,fn=line.split(maxsplit=3);a,n=int(a,16),int(n,16)
 if n>sy.get(a,(0,''))[0]:sy[a]=(n,fn)
keys=sorted(sy)
for p in sorted(d.glob('run-*.log')):
 s=p.read_text();assert 'verified 120 original demo frames' in s
 for f,pc in re.findall(r'^\[FRAME_PC\] (\d+) (\w+)$',s,re.M):
  if not 31<=int(f)<=120:continue
  pc=int(pc,16);i=bisect.bisect_right(keys,pc)-1
  if i>=0:
   a=keys[i];n,fn=sy[a]
   if pc<a+n:add(host,fn)
print('named sub_ samples device/host',sum(dev.values()),sum(host.values()))
for k,n in dev.most_common(12):print(f'{k:08X} {n:3} {host[k]:3}')
