"""Exclusive CPU samples in functions containing large target switches. This is not switch cost."""
from pathlib import Path
from collections import Counter
from bisect import bisect_right
import re,runpy
pat=runpy.run_path(str(Path(__file__).with_name('jump-buckets.py')))['pat']
owners=set()
for u in [0,2]:
 src=Path(f'build/switch-runtime/gen/recomp_{u:04}.c').read_text()
 for fn,b in re.findall(r'^void (\w+)\(void\)\n\{(.*?)^\}',src,re.M|re.S):
  if any(int(m[2])>=16 for m in pat.finditer(b)):owners.add(fn)
d=Path('build/switch-runtime/core-perf/opening-compact-profile')
sym={}
for line in (d/'symbols.txt').read_text().splitlines():
 addr,size,_,name=line.split(maxsplit=3);addr,size=int(addr,16),int(size,16)
 if size>sym.get(addr,(0,''))[0]:sym[addr]=(size,name)
keys=sorted(sym)
for i in range(1,5):
 s=(d/f'run-{i}.log').read_text();assert 'verified 120 original demo frames' in s
 hits=Counter();total=0
 for frame,pc in re.findall(r'^\[FRAME_PC\] (\d+) (\w+)$',s,re.M):
  if not 31<=int(frame)<=120:continue
  total+=1;pc=int(pc,16);j=bisect_right(keys,pc)-1
  if j<0:continue
  start=keys[j];size,name=sym[start]
  fn=name.split('.')[0].removeprefix('ngb_reg_')
  if pc<start+size and fn in owners:hits[fn]+=1
 print(i,sum(hits.values()),'/',total,'delivered thread samples',dict(hits))
