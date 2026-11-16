"""Which primary guest bodies changed? Count historical named leaf samples, never cycles."""
from collections import Counter
from pathlib import Path
import struct
root=Path('build/switch-runtime/core-perf')
def bodies(path):
 b=path.read_bytes()
 def read(fmt,off):return struct.unpack_from('<'+fmt,b,off)
 sections=[read('IIQQQQIIQQ',read('Q',40)[0]+64*i) for i in range(read('H',60)[0])]
 out={}
 for s in sections:
  if s[1]!=2:continue
  tab=sections[s[6]][4]
  for i in range(s[4],s[4]+s[5],24):
   off,info,_,section,addr,size=read('IBBHQQ',i)
   if info&15!=2 or not size:continue
   name=b[tab+off:b.index(b'\0',tab+off)].decode()
   if not name.startswith('ngb_reg_') or '.' in name:continue
   pos=sections[section][4]+addr
   out[name.removeprefix('ngb_reg_')]=b[pos:pos+size]
 return out
changed=set(); covered=set()
for unit in (2,10,16,28,29):
 a,b=[bodies(root/d/f'recomp_{unit:04}.c.o') for d in ('opening-partition-pgo','opening-partition-no-unroll')]
 assert a.keys()==b.keys() and len(a)==250 and not covered.intersection(a)
 diff=[n for n in a if a[n]!=b[n]]
 print(unit,'changed primary instruction bytes in',len(diff),'of',len(a),'functions; total size delta',sum(len(b[n])-len(a[n]) for n in diff))
 changed.update(diff);covered.update(a)
rows=[l.split('\t') for l in (root/'opening-setup/leaf-budget.tsv').read_text().splitlines() if '\t' in l]
for lo,hi in ((1,30),(31,120)):
 group=Counter(r[3].removeprefix('ngb_reg_') for r in rows if lo<=int(r[0])<=hi and int(r[1])==1)
 print(lo,hi,'historical device leaf samples in changed bodies / five units / delivered',sum(group[k] for k in changed),sum(group[k] for k in covered),sum(group.values()))
