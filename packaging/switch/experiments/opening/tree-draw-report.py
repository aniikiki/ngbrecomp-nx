"""Inclusive CPU of calls at seven disjoint source locations (cost is not potential saving)."""
from pathlib import Path
import re
s=Path('build/switch-runtime/core-perf/opening-tree-draw-cost/budget.log').read_text()
assert 'verified 120 original demo frames' in s
rows=[tuple(map(int,r)) for r in re.findall(r'^\[TREE_COST\] (\d+) (\d+) calls=(\d+) samples=(\d+) ns=(\d+) blanks=(\d+) blank_ns=(\d+) cross=(\d+)$',s,re.M)]
assert [(r[0],r[1]) for r in rows]==[(f,i) for f in (30,120) for i in range(7)]
for f,i,c,n,t,b,z,x in rows:
 label=['3B0:308130','3B0:30B020','3B0:307B80(a)','3B0:307B80(b)','510:308130','510:30B020','510:3078B0'][i]
 frames=30 if f==30 else 90
 print(f,label,'calls/frame',round(c/frames,2),'samples',n,'cross',x,'ms/frame',round(c/frames*(t/n-z/b)*1e-6,5) if n and b and not x else ('unused' if c==0 else 'insufficient'))
