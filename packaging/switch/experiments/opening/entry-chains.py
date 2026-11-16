"""Pack frequently consecutive entry points in chains; train only on flips 1..30."""
import re,collections,subprocess
from pathlib import Path
def data(base):
 d=base/'core-perf';s=(d/'opening-entry-stream/budget.log').read_text()
 assert 'verified 120 original demo frames' in s and re.findall(r'^\[STREAM_TOTAL\] (\d+) .*?dropped=(\d+)$',s,re.M)==[('30','0'),('120','0')]
 sy={}
 for line in (d/'opening-compact-profile/symbols.txt').read_text().splitlines():
  a,l,_,name=line.split(maxsplit=3)
  if re.fullmatch(r'ngb_reg_sub_[0-9A-F]+',name):sy[int(name[12:],16)]=(int(a,16),int(l,16))
 edge={f:collections.Counter() for f in [30,120]}
 for f,a,b,n in re.findall(r'^\[STREAM_EDGE\] (\d+) (\w+) (\w+) (\d+)$',s,re.M):
  a,b=int(a,16),int(b,16)
  if a!=b and a in sy and b in sy:edge[int(f)][tuple(sorted([a,b]))]+=int(n)
 return sy,edge
def script(base,out):
 sy,e=data(base);owner={};chains={};freq=collections.Counter()
 for (a,b),n in e[30].items():freq[a]+=n;freq[b]+=n
 for (a,b),n in e[30].most_common():
  if n<40:break
  x=owner.get(a,a);y=owner.get(b,b)
  if x==y:continue
  A=chains.get(x,[a]);B=chains.get(y,[b])
  if a not in (A[0],A[-1]) or b not in (B[0],B[-1]):continue
  if sum(sy[v][1] for v in A+B)>65536:continue
  # Pick an orientation preserving the interior order up to whole-chain reversal.
  left=A if A[-1]==a else A[::-1];right=B if B[0]==b else B[::-1]
  joint=left+right
  if sy[a][1]>sy[b][1]:joint.reverse()
  chains.pop(y,None);chains[x]=joint
  for v in joint:owner[v]=x
 groups=sorted(chains.values(),key=lambda c:-sum(freq[v] for v in c)/sum(sy[v][1] for v in c))
 order=[v for c in groups for v in c]
 assert len(order)==len(set(order)) and len(order)>100
 out.write_text('SECTIONS { .text.ngb_opening ALIGN(4096) : {\n'+''.join(f' *recomp_*.c.o(.text.sub_{v:08X})\n' for v in order)+'} } INSERT BEFORE .text;\n')
def verify(base,elf):
 _,edges=data(base)
 for f in (elf.parent/'original',elf):
  s=subprocess.check_output(['nm','-n',f],text=True)
  a={int(n,16):int(v,16) for v,n in re.findall(r'^([\da-f]+) [tT] ngb_reg_sub_([\dA-F]+)$',s,re.M)}
  e=edges[120];assert all(i in a and j in a for i,j in e)
  print(f.name,'held-out eligible distinct-entry transitions',sum(e.values()),'same 4 KiB page',sum(w for (i,j),w in e.items() if a[i]//4096==a[j]//4096),'within 64 KiB',sum(w for (i,j),w in e.items() if abs(a[i]-a[j])<65536),flush=True)
