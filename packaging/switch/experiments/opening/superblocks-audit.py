"""Check whether scheduled code actually changed at previously sampled guest functions."""
from pathlib import Path
import struct,runpy,io,contextlib
from collections import Counter
with contextlib.redirect_stdout(io.StringIO()):
 q=runpy.run_path(str(Path(__file__).with_name('translation-pc-budget.py')))
def funcs(obj):
 b=obj.read_bytes()
 sh=[struct.unpack_from('<IIQQQQIIQQ',b,struct.unpack_from('<Q',b,40)[0]+64*i) for i in range(struct.unpack_from('<H',b,60)[0])]
 out={}
 for st in sh:
  if st[1]!=2:continue
  tab=sh[st[6]][4]
  for i in range(st[4],st[4]+st[5],24):
   n,info,_,sec,v,sz=struct.unpack_from('<IBBHQQ',b,i)
   if not sz or info&15!=2:continue
   name=b[tab+n:b.index(b'\0',tab+n)].decode()
   if name.startswith('ngb_reg_'):out[name]=b[sh[sec][4]+v:sh[sec][4]+v+sz]
 return out
counts=Counter()
for u in (2,10,16,26,39):
 old,new=[funcs(q['q']['root']/group/f'recomp_{u:04}.c.o') for group in ('opening-compact-loops','opening-superblocks')]
 assert old.keys()==new.keys()
 for n in old:counts['functions']+=1;counts['changed functions']+=int(old[n]!=new[n])
 for (n,o),_ in q['samples']:
  if n not in old:continue
  assert old[n]==q['code'][n]
  if q['tags'][n].get(o//4)=='page table load':
   counts['samples at original page loads']+=1
   counts['in changed functions']+=int(old[n]!=new[n])
print(dict(counts))
