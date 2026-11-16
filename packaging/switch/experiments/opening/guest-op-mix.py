"""Join compact-profile exclusive guest PCs to instructions in the re-linked same-layout ELF.
Pipe in GNU objdump -d output. Counts are sampled locations, not cycle attribution."""
import re,bisect,sys
from pathlib import Path
from collections import Counter,defaultdict
d=Path('build/switch-runtime/core-perf/opening-compact-profile')
sy={}
for l in (d/'symbols.txt').read_text().splitlines():
 a,n,_,fn=l.split(maxsplit=3);a,n=int(a,16),int(n,16)
 if n>sy.get(a,(0,''))[0]:sy[a]=(n,fn)
keys=sorted(sy);hits=defaultdict(list)
for i in range(1,5):
 s=(d/f'run-{i}.log').read_text();assert 'reason=verified 120 original demo frames' in s
 for f,p in re.findall(r'^\[FRAME_PC\] (\d+) (\w+)$',s,re.M):
  pc=int(p,16);j=bisect.bisect_right(keys,pc)-1
  if j<0:continue
  a=keys[j];n,fn=sy[a]
  if pc<a+n and fn.startswith(('ngb_reg_sub_','ngb_reg_d3d_orig_')):hits[pc].append((int(f)>30,fn))
counts=Counter();functions=defaultdict(set);seen=set();opcounts=Counter()
neighbors={a+off for a in hits for off in range(-16,17,4)}
detail={}
for l in sys.stdin:
 m=re.match(r'^\s*([0-9a-f]+):\s+[0-9a-f]{8}\s+(\S+)\s*(.*)',l)
 if not m:continue
 pc=int(m[1],16)
 if pc in neighbors: detail[pc]=m[2],m[3]
 if pc not in hits:continue
 op,arg=m[2],m[3];base=re.search(r'\[(\w+)',arg)
 if base: k='memory '+(base[1] if base[1] in ('sp','x27','x29') else 'other base')
 elif op in ('bl','blr','ret','br','b') or op.startswith(('b.','cb','tb')):k='control '+op.split('.')[0]
 elif op.startswith('f'):k='floating point'
 else:k='other '+op
 seen.add(pc)
 for phase,fn in hits[pc]:
  counts[phase,k]+=1;functions[phase,k].add(fn);opcounts[phase,k,op]+=1
assert seen==set(hits)
for phase in (False,True):
 print('frames', '31..120' if phase else '1..30', 'guest samples',sum(n for (p,k),n in counts.items() if p==phase))
 for (p,k),n in counts.most_common():
  if p==phase and n>=3: print(k,n,'functions',len(functions[p,k]),'opcodes',[(o,v) for (q,c,o),v in opcounts.most_common() if (q,c)==(p,k)][:5])

# Do not cross function boundaries, or treat nearby calls as proof of spilling.
summary=Counter();regs=Counter()
for pc,rows in hits.items():
 op,arg=detail[pc]
 if not re.search(r'\[sp(?:,|\])',arg):continue
 start=keys[bisect.bisect_right(keys,pc)-1];end=start+sy[start][0]
 calls=[]
 for q in range(max(start,pc-16),min(end,pc+20),4):
  ins,operand=detail.get(q,('',''))
  if ins in ('bl','blr'):calls.append((abs(q-pc),q-pc,operand))
 if calls:
  _,off,dst=min(calls)
  name=dst.split('<')[-1].split('>')[0]
  label='checkpoint' if 'checkpoint' in name else 'generated guest' if name.startswith('ngb_reg_') else name
 else:label='no call within four instructions'
 for phase,fn in rows:
  if phase:summary[label]+=1;regs[arg.split('[')[0].rstrip(', ')]+=1
print('late SP operands by nearest static call',summary.most_common())
print('late SP operands by register tuple',regs.most_common(20))
# Describe the nearest straight-line writer of each otherwise unclassified base.
writers=Counter();examples=defaultdict(list)
for pc,rows in hits.items():
 op,arg=detail[pc];m=re.search(r'\[(x\d+)',arg)
 if not m or m[1] in ('x27','x29'):continue
 base=m[1];start=keys[bisect.bisect_right(keys,pc)-1];label='unknown'
 for q in range(pc-4,max(start-4,pc-20),-4):
  ins,args=detail[q]
  if ins in ('b','bl','blr','br','ret') or ins.startswith(('b.','tb','cb')):break
  # Only recognize single destinations. Do not step past an unknown writer.
  if re.match(r'(?:x|w)'+base[1:]+r'\b',args):
   if ins.startswith(('st','cmp','tst')):break
   label=ins
   if ins=='add' and re.search(r',\s*x26\b',args):label+=' with guest RAM base x26'
   if ins=='adrp':label='static address page'
   break
  if ins.startswith('ldp') and re.search(r',\s*'+base+r'\b',args):break
 for phase,fn in rows:
  if phase:
   writers[label]+=1
   if len(examples[label])<3:examples[label].append((fn,hex(pc),arg))
print('late other bases, nearest syntactic writer (within four instructions)',writers.most_common())
print('examples',dict(examples))
