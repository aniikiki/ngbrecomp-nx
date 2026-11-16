"""Count exclusive compact-profile PCs actually in second-tier generated functions."""
import bisect,re,struct
from pathlib import Path
from collections import Counter
root=Path('build/switch-runtime/core-perf');d=root/'opening-compact-profile'
units=[28,1,0,29,15]
def names_size(obj):
 b=obj.read_bytes();u=lambda fmt,pos:struct.unpack_from('<'+fmt,b,pos)
 sh=[u('IIQQQQIIQQ',u('Q',40)[0]+j*64) for j in range(u('H',60)[0])]
 out={}
 for s in sh:
  if s[1]!=2:continue
  tab=sh[s[6]][4]
  for a in range(s[4],s[4]+s[5],24):
   off,info,_,sec,val,n=u('IBBHQQ',a)
   if info&15!=2 or not n:continue
   name=b[tab+off:b.index(b'\0',tab+off)].decode()
   if name.startswith('ngb_reg_'):out[name]=n
 return out
owner={};groups=['opening-full-page','opening-page-next-o3','opening-compact-next']
for i in units:
 obj=f'recomp_{i:04}.c.o';sets=[]
 for g in groups:
  p=root/g/obj
  if p.exists():sets.append(names_size(p))
 for n in sets[0]:assert n not in owner;owner[n]=i
 for other in sets[1:]:assert set(sets[0])==set(other)
 print(i,'guest function bytes O2 / O3 / compact (if built)',*[sum(m.values()) for m in sets])
sy={}
for l in (d/'symbols.txt').read_text().splitlines():
 a,n,_,fn=l.split(maxsplit=3);a,n=int(a,16),int(n,16)
 if n>sy.get(a,(0,''))[0]:sy[a]=(n,fn)
keys=sorted(sy)
for lo,hi in [(1,30),(31,120)]:
 c=Counter();tot=0
 for i in range(1,5):
  s=(d/f'run-{i}.log').read_text();assert 'verified 120 original demo frames' in s
  for f,pc in re.findall(r'^\[FRAME_PC\] (\d+) (\w+)$',s,re.M):
   if not lo<=int(f)<=hi:continue
   tot+=1;pc=int(pc,16);j=bisect.bisect_right(keys,pc)-1
   if j<0:continue
   a=keys[j];n,fn=sy[a]
   if pc<a+n and fn in owner:c[owner[fn]]+=1
 print(lo,hi,dict(sorted(c.items())),'hits / delivered',sum(c.values()),tot)
