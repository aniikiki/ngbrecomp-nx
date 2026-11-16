"""Map the specific 16-byte relay to historical delivered PCs; no timing or hit extrapolation."""
import struct,collections,contextlib,io,runpy
from pathlib import Path
with contextlib.redirect_stdout(io.StringIO()):
 q=runpy.run_path(str(Path(__file__).with_name('compact-entry-edges.py')))
def relays(b):
 w=struct.unpack('<'+'I'*(len(b)//4),b)
 for i in range(len(w)-2):
  a,s=w[i:i+2]
  if a&0xffc00000!=0xa9400000 or s&0xffc003e0!=0xa90003e0:continue
  if a&0x7c1f!=s&0x7c1f or (a>>5)&31==31:continue
  slot=(s>>15)&127
  if slot>=64:continue
  j=i+2
  if w[j]&0xffc00000==0x91000000 or w[j]&0x9f000000==0x90000000 or w[j]&0xffe0ffe0==0xaa0003e0:j+=1
  if j==len(w):continue
  v=w[j]
  if v&0xffc003e0==0x3dc003e0 and ((v>>10)&4095)*16==slot*8:
   yield (i,i+1,j)
hit=collections.Counter()
for (fn,o),_ in q['samples']:hit[fn,o]+=1
def scan(obj):
 b=obj.read_bytes();sh=[struct.unpack_from('<IIQQQQIIQQ',b,struct.unpack_from('<Q',b,40)[0]+i*64) for i in range(struct.unpack_from('<H',b,60)[0])]
 count=sample=0;covered=set()
 for st in sh:
  if st[1]!=2:continue
  tab=sh[st[6]][4]
  for i in range(st[4],st[4]+st[5],24):
   name,info,_,idx,v,n=struct.unpack_from('<IBBHQQ',b,i)
   if info&15!=2 or not n or n%4:continue
   fn=b[tab+name:b.index(b'\0',tab+name)].decode()
   if not fn.startswith('ngb_reg_') or (idx,v) in covered:continue
   covered.add((idx,v));base=sh[idx][4]+v
   for ix in relays(b[base:base+n]):
    count+=1;sample+=sum(hit[fn,o*4] for o in ix)
 return count,sample
root=q['root'];rows=[]
for u in range(47):
 g='opening-compact-loops' if u in (2,10,16,26,39) else 'opening-full-page'
 rows.append((u,*scan(root/g/f'recomp_{u:04}.c.o')))
for title,r in [('tested',[x for x in rows if x[0] in (0,28,29)]),('other',[x for x in rows if x[0] not in (0,28,29)])]:
 print(title,'static',sum(x[1] for x in r),'sampled at the three memory instructions',sum(x[2] for x in r),'top units',sorted(r,key=lambda x:(x[2],x[1]),reverse=True)[:7])
