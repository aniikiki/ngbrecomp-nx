"""Join sampled PC and LR from the same interrupt to compact guest object code."""
from pathlib import Path
from bisect import bisect_right
from collections import Counter
import re,struct
root=Path('build/switch-runtime/core-perf'); d=root/'opening-compact-profile'
sym={}
for row in (d/'symbols.txt').read_text().splitlines():
 a,n,_,name=row.split(maxsplit=3);a,n=int(a,16),int(n,16)
 if n>sym.get(a,(0,None))[0]:sym[a]=(n,name)
keys=sorted(sym)
def loc(pc):
 j=bisect_right(keys,pc)-1
 if j>=0:
  a=keys[j];n,name=sym[a]
  if pc<a+n:return name,pc-a
 return '',0
samples=[]
for i in range(1,5):
 log=(d/f'run-{i}.log').read_text();assert 'verified 120 original demo frames' in log
 for f,p,l in re.findall(r'^\[FRAME_LR\] (\d+) (\w+) (\w+)$',log,re.M):
  dst=loc(int(p,16))
  if 31<=int(f)<=120 and dst[0].startswith(('ngb_reg_sub_','ngb_reg_d3d_orig_')):
   samples.append((dst,loc(int(l,16)-4)))
assert len(samples)==664
wanted={n for pair in samples for n,_ in pair}; code={}; calls={}
for unit in range(47):
 group='opening-compact-loops' if unit in (2,10,16,26,39) else 'opening-full-page'
 b=(root/group/f'recomp_{unit:04}.c.o').read_bytes()
 u=lambda fmt,pos:struct.unpack_from('<'+fmt,b,pos)
 sh=[u('IIQQQQIIQQ',u('Q',40)[0]+64*j) for j in range(u('H',60)[0])]
 names={}; sections={}
 for st in sh:
  if st[1]!=2:continue
  tab=sh[st[6]][4]
  for j,idx in enumerate(range(st[4],st[4]+st[5],24)):
   off,info,_,sec,val,size=u('IBBHQQ',idx);p=tab+off
   n=b[p:b.index(b'\0',p)].decode();names[j]=n
   if n in wanted and size and info&15==2:
    sections[sec]=(n,val);code[n]=b[sh[sec][4]+val:sh[sec][4]+val+size]
 for r in sh:
  if r[1]!=4 or r[7] not in sections:continue
  n,v=sections[r[7]]
  for j in range(r[4],r[4]+r[5],24):
   off,info,add=u('QQq',j)
   if info&0xffffffff==283 and not add:calls[n,off-v]=names[info>>32]
c=Counter();edges=Counter(); offsets=Counter()
for (n,o),src in samples:
 op=int.from_bytes(code[n][o:o+4],'little')
 if op & 0xffc07fff not in (0xa9807bfd,0xa9007bfd):continue
 c['save']+=1;offsets[o]+=1
 if calls.get(src)==n:
  c['direct']+=1;edges[src[0],n]+=1
 else:c['unresolved']+=1
print(c,offsets.most_common(12));print('edges',len(edges),edges.most_common(15))
