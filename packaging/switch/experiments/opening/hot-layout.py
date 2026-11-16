"""Link the actual opening working set together, independent of object-unit order.
No duplicated game code or profile counters in the timed executable. The edge
weights are placement heuristics from direct calls plus measured entry counts,
not measured edge frequencies. Use a separate output section to audit placement."""
import re,collections
from pathlib import Path
def script(base,out):
 regs=base/'native-regs';counts=collections.Counter();edges=collections.Counter();sections={}
 frames=set()
 for frame,ls in re.findall(r'^\[ENTRY_MIX\] (\d+) (.*)$',(base/'core-perf/opening-setup/entry-mix.log').read_text(),re.M):
  if 31<=int(frame)<=120:
   frames.add(int(frame))
   for va,n in re.findall(r'([0-9a-f]+):(\d+)',ls):counts[int(va,16)]+=int(n)
 assert frames==set(range(31,121))
 for f in sorted(regs.glob('recomp_*.c.gated.s')):
  owner=None
  for ln in f.open():
   if ln.startswith('\t.section'):
    m=re.match(r'\s*\.section\s+\.text\.(sub_([0-9A-F]+)),',ln)
    owner=int(m[2],16) if m and int(m[2],16) in counts else None
    if owner is not None:
     assert owner not in sections
     sections[owner]=(f.name.removesuffix('.gated.s')+'.o','.text.'+m[1])
   if owner is not None:
    m=re.match(r'\s*(?:bl|b)\s+ngb_reg_sub_([0-9A-F]+)\s*$',ln)
    if m:
     dest=int(m[1],16)
     if dest!=owner and dest in counts:edges[owner,dest]+=1
 clusters={k:[k] for k in sections};belong={k:k for k in sections}
 for (a,b),_ in sorted(edges.items(),key=lambda kv:-min(counts[kv[0][0]]*kv[1],counts[kv[0][1]])):
  if b not in belong:continue
  x,y=belong[a],belong[b]
  if x==y or clusters[x][-1]!=a or clusters[y][0]!=b:continue
  for k in clusters[y]:belong[k]=x
  clusters[x].extend(clusters.pop(y))
 order=[v for c in sorted(clusters.values(),key=lambda c:-max(counts[v] for v in c)) for v in c]
 assert len(order)==len(set(order))==len(sections)>100
 out.write_text('SECTIONS { .text.ngb_opening ALIGN(64) : {\n'+''.join(' *'+sections[v][0]+'('+sections[v][1]+')\n' for v in order)+'} } INSERT BEFORE .text;\n')
 print('grouped private opening functions:',len(order),'observed entries covered:',sum(counts[v] for v in order),'of',sum(counts.values()),flush=True)
if __name__=='__main__':
 import sys
 script(Path(sys.argv[1]),Path(sys.argv[2]))
