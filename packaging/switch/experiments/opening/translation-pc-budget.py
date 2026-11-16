"""Count sampled PCs on identifiable address checks. Only follow contiguous, data-linked A64 ops.
The anchor is x27's indexed end-address table, not the later real guest load or store."""
import collections,contextlib,io,runpy,struct
from pathlib import Path
with contextlib.redirect_stdout(io.StringIO()):
 q=runpy.run_path(str(Path(__file__).with_name('compact-entry-edges.py')))
code=q['code']; samples=q['samples']
counts=collections.Counter();funcs=collections.defaultdict(set)
def classify(b):
 w=struct.unpack('<'+'I'*(len(b)//4),b)
 tags={}
 for i,v in enumerate(w):
  if v&0xffc003e0==0xb9400360:  # LDR Wt,[X27,#imm]: constant-index entry
   tags[i]='fixed page table load';continue
  # LDR Wt,[X27,Xm,LSL #2]
  if v & 0xffe0ffe0 != 0xb8607b60:continue
  tags[i]='page table load';idx=(v>>16)&31;end=v&31
  va=None
  if i and w[i-1]&0xfffffc1f==0x530c7c00|idx:
   va=(w[i-1]>>5)&31;tags[i-1]='page index shift'
  if i+2>=len(w):continue
  cmp=w[i+1];branch=w[i+2]
  if cmp&0xffe0fc1f!=0x6b00001f:continue
  left=(cmp>>5)&31;right=(cmp>>16)&31
  if right==end and (va is None or left==va) and branch&0xff00001f in (0x54000002,0x54000003):addr=left
  elif left==end and (va is None or right==va) and branch&0xff00001f in (0x54000008,0x54000009):addr=right
  else:continue
  tags[i+1]='bound compare';tags[i+2]='bound branch'
  if i+3>=len(w):continue
  m=w[i+3]
  if m&0xfffffc00 not in (0x92407800,0x12007800) or (m>>5)&31!=addr:continue
  tags[i+3]='alias mask'
  if i+4<len(w):
   add=w[i+4]
   if add&0xffe0ffe0==0x8b000340 and (add>>16)&31==(m&31):tags[i+4]='RAM base add'
 return tags
tags={n:classify(b) for n,b in code.items() if len(b)%4==0}
for (fn,off),_ in samples:
 tag=tags.get(fn,{}).get(off//4)
 if tag:counts[tag]+=1;funcs[tag].add(fn)
assert counts['page table load']+counts['fixed page table load']==145
print('31..120:',sum(counts.values()),'samples at matched instructions out of 1142 delivered,',len(samples),'in guest routines')
for tag,n in counts.most_common():print(tag,n,'across',len(funcs[tag]),'functions')
