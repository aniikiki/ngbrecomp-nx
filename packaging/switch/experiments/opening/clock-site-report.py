"""Pair only samples inside the VDSO clock with the wrapper active on that thread."""
from pathlib import Path
from bisect import bisect_right
from collections import Counter
import re,sys
d=Path('build/switch-runtime/core-perf/opening-frame-pc');s=(d/'distribution.log').read_text()
assert 'verified 120 original demo frames' in s
table={}
for l in (d/'text-symbols.txt').read_text().splitlines():
 a,n,_,name=l.split(maxsplit=3);a=int(a,16);n=int(n,16)
 if n and n>table.get(a,(0,''))[0]:table[a]=(n,name)
keys=sorted(table)
vdso=Counter((int(f),pc) for f,pc in re.findall(r'^\[FRAME_MODULE\] (\d+) (\w+) \w+ linux-vdso.so.1 __kernel_clock_gettime$',s,re.M))
total=sum(vdso.values());bins=[Counter(),Counter()]
for f,pc,ra in re.findall(r'^\['+('CLOCK_PARENT' if '--parent' in sys.argv else 'CLOCK_ORIGIN')+r'\] (\d+) (\w+) (\w+)$',s,re.M):
 f=int(f)
 if not vdso[f,pc]:continue
 vdso[f,pc]-=1
 addr=int(ra,16)-4;idx=bisect_right(keys,addr)-1
 name='unresolved'
 if idx>=0 and addr<keys[idx]+table[keys[idx]][0]:name=table[keys[idx]][1]
 bins[f>30][name,ra]+=1
for (f,pc),n in vdso.items():
 if n:bins[f>30]['no wrapped origin','-']+=n
assert sum(map(lambda c:sum(c.values()),bins))==total
for win,c in zip(('1..30','31..120'),bins):print(win,sum(c.values()),c.most_common())
