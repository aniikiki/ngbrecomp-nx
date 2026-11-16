"""Locate compact ARM guest samples in bounded, directly connected natural loops.
Use only functions without indirect jumps; BL/BLR represent a returning call.
Report exclusive sample locations, not the cost of a poll or a Switch speedup.
"""
from pathlib import Path
from collections import Counter,defaultdict
import re,runpy,contextlib,io,struct
p=Path(__file__).parent
with contextlib.redirect_stdout(io.StringIO()):q=runpy.run_path(str(p/'compact-entry-edges.py'))
def signed(i,b):return i-(1<<b) if i>>(b-1) else i
def loops(b):
 w=struct.unpack('<'+'I'*(len(b)//4),b);n=len(w);leaders={0};edges={}
 for i,v in enumerate(w):
  if v&0xfffffc1f==0xd61f0000:return [] # BR: unknown intra-function targets
  if v&0xfc000000==0x14000000:s=[i+signed(v&0x3ffffff,26)]
  elif v&0xff000010==0x54000000 or v&0x7e000000==0x34000000:s=[i+1,i+signed((v>>5)&0x7ffff,19)]
  elif v&0x7e000000==0x36000000:s=[i+1,i+signed((v>>5)&0x3fff,14)]
  elif v&0xfffffc1f==0xd65f0000:s=[]
  else:continue
  # In a relocatable object an external tail branch often has imm=0.
  # Do not classify placeholders (or a true self-spin) as a loop.
  s=[j for j in s if j!=i]
  edges[i]=s;leaders.update(j for j in [i+1,*s] if 0<=j<n)
 ls=sorted(leaders);pred=defaultdict(set);succ={};blocks={}
 for a,z in zip(ls,ls[1:]+[n]):
  blocks[a]=(a,z);succ[a]={j for j in edges.get(z-1,[z]) if 0<=j<n}
  for j in succ[a]:pred[j].add(a)
 seen={0};todo=[0]
 while todo:
  for j in succ[todo.pop()]-seen:seen.add(j);todo.append(j)
 # Only blocks with an incoming backward edge need a dominance test:
 # can we reach the tail from function entry without visiting this header?
 groups=defaultdict(set)
 for a in seen:
  for h in succ[a]:
   if h>a:continue
   visited={h};work=[0] if h!=0 else []
   while work:
    j=work.pop()
    if j in visited:continue
    visited.add(j);work.extend(succ[j]-visited)
   if a!=h and a in visited:continue
   body={h,a};work=[a] if h!=a else []
   while work:
    for j in (pred[work.pop()]&seen)-body:body.add(j);work.append(j)
   groups[h].update(body)
 return [(h,frozenset(i for a in bb for i in range(*blocks[a]))) for h,bb in groups.items()]
# Collect PCs in the two training and the two held-out runs separately.
hits=[Counter(),Counter()]
for j in range(1,5):
 t=(q['d']/f'run-{j}.log').read_text()
 for f,pc in re.findall(r'^\[FRAME_PC\] (\d+) (\w+)$',t,re.M):
  if 31<=int(f)<=120:
   name,off=q['loc'](int(pc,16))
   if name in q['code']:hits[(j-1)//2][name,off//4]+=1
rank=[Counter(),Counter()]
for name,b in q['code'].items():
 if not name.startswith(('ngb_reg_sub_','ngb_reg_d3d_orig_')) or len(b)%4:continue
 ls=sorted(loops(b),key=lambda x:(len(x[1]),x[0]))
 for k in (0,1):
  for (fn,i),weight in hits[k].items():
   if fn!=name:continue
   for h,ops in ls:
    if i in ops:
     rank[k][name,4*h,len(ops)]+=weight;break
for key,n in rank[0].most_common(12):print(key[0],hex(key[1]),key[2],'instructions, train/holdout',n,rank[1][key])
print('exclusive guest PCs assigned to identified loops:',*[sum(x.values()) for x in rank])
