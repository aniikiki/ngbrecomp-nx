"""Summarize GCC precise blocks for a chosen unit set. Not device instructions or elapsed time."""
import sys,re
from pathlib import Path
from collections import Counter
s=Path(sys.argv[1]).read_text()
units=[int(u) for u in sys.argv[2:]]
totals={int(u):int(total) for u,total in re.findall(r'^unit (\d+) .*weighted static instructions (\d+)$',s,re.M)}
owner=Counter();cats=Counter();unit=Counter()
for u,fn,k,v in re.findall(r'^ROW (\d+) (\w+) (\S+) (\d+)$',s,re.M):
 u=int(u);v=int(v)
 if u not in units:continue
 owner[fn]+=v;cats[k]+=v;unit[u]+=v
assert all(unit[u]==totals[u] and totals[u]>0 for u in units)
print('units:',units,'precise-block weighted pre-ABI instructions:',sum(unit.values()))
print('by opcode class:',cats)
print('leaders:',owner.most_common(10))
