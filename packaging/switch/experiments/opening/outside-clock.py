"""CLOCK_PARENT is sparse; use frame/PC only if every matching sample is outside."""
from pathlib import Path
from collections import Counter,defaultdict
from bisect import bisect_right
import re
d=Path('build/switch-runtime/core-perf/opening-xdk-pc-scope')
sy={}
for row in (d/'symbols.txt').read_text().splitlines():
 a,n,_,k=row.split(maxsplit=3);a,n=int(a,16),int(n,16)
 if n>sy.get(a,(0,''))[0]:sy[a]=n,k
keys=sorted(sy)
def sym(pc):
 a=keys[bisect_right(keys,pc)-1];return sy[a][1] if a<=pc<a+sy[a][0] else '<unknown>'
tot=Counter()
for i in range(1,5):
 s=(d/f'run-{i}.log').read_text();depths=defaultdict(set)
 for f,dp,pc in re.findall(r'^\[D3D_SCOPE_PC\] (\d+) (\d+) (\w+)$',s,re.M):depths[f,pc].add(int(dp)!=0)
 mods={(f,pc):fn for f,pc,fn in re.findall(r'^\[FRAME_MODULE\] (\d+) (\w+) \w+ \S+ (\S+)$',s,re.M)}
 for f,pc,outer in re.findall(r'^\[CLOCK_PARENT\] (\d+) (\w+) (\w+)$',s,re.M):
  if int(f)>30 and depths[f,pc]=={False} and mods.get((f,pc))=='__kernel_clock_gettime':
   tot[sym(int(outer,16)-4)]+=1
print(tot)
