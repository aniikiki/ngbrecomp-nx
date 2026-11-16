"""Match dynamic samples to actually recompiled functions, not source unit address ranges."""
from pathlib import Path
import struct,runpy,sys
p=Path(__file__).parent;d=Path('build/switch-runtime/core-perf')
def symbols(f):
 b=f.read_bytes();u=lambda fmt,pos:struct.unpack_from('<'+fmt,b,pos)
 sh=[u('IIQQQQIIQQ',u('Q',40)[0]+64*i) for i in range(u('H',60)[0])]
 out={}
 for sec in sh:
  if sec[1]!=2:continue
  tab=sh[sec[6]][4]
  for i in range(sec[4],sum(sec[4:6]),24):
   off,info,_,_,_,size=u('IBBHQQ',i)
   if info&15!=2 or not size:continue
   n=b[tab+off:b.index(b'\0',tab+off)].decode()
   if n.startswith('ngb_reg_'):out[n]=size
 return out
owners=set();nbase=nalt=0
for i in (2,10,16,26,39):
 name=f'recomp_{i:04}.c.o'
 base=symbols(d/'opening-compact-loops'/name);assert not owners.intersection(base);owners.update(base);nbase+=sum(base.values())
 if '--before' not in sys.argv:
  alt=symbols(d/'opening-size-hot'/name);assert base.keys()==alt.keys();nalt+=sum(alt.values())
print('guest symbols',len(owners),'baseline bytes',nbase,'candidate bytes',nalt if nalt else 'pending')
for lo,(halves,total) in runpy.run_path(str(p/'copy-profile-rank.py'))['analyze'](d/'opening-copy-profile').items():
 print('from frame',lo,'hits',sum(v for half in halves for k,v in half.items() if k in owners),'delivered',sum(total))
