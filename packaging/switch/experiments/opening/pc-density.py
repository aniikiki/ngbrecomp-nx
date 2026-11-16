"""Pack at most 32KiB of sampled function bodies by repeated exclusive hit density."""
import re,bisect
from pathlib import Path
from collections import Counter
def script(base,out):
 d=base/'core-perf/opening-hot-profile'
 sy={}
 for l in (d/'symbols.txt').read_text().splitlines():
  a,n,_,name=l.split(maxsplit=3);a=int(a,16);n=int(n,16)
  if n>sy.get(a,(0,''))[0]:sy[a]=(n,name)
 keys=sorted(sy);hits=[];sizes={}
 for i in (1,2):
  s=(d/f'run-{i}.log').read_text();assert 'verified 120 original demo frames' in s
  c=Counter()
  for f,pc in re.findall(r'^\[FRAME_PC\] (\d+) (\w+)$',s,re.M):
   if not 31<=int(f)<=120:continue
   pc=int(pc,16);j=bisect.bisect_right(keys,pc)-1
   if j<0:continue
   a=keys[j];n,name=sy[a]
   if pc<a+n and re.fullmatch(r'ngb_reg_sub_[A-F0-9]+',name):
    name=name.removeprefix('ngb_reg_');c[name]+=1;sizes[name]=n
  hits.append(c)
 selected=[];used=0
 for name in sorted(hits[0].keys()&hits[1].keys(),key=lambda n:(-(hits[0][n]+hits[1][n])/sizes[n],n)):
  size=(sizes[name]+63)&~63
  if used+size<=32768:selected.append(name);used+=size
 assert len(selected)>4
 out.write_text('SECTIONS { .text.ngb_opening ALIGN(64) : {\n'+''.join(f' *recomp_*.c.o(.text.{n})\n' for n in selected)+'} } INSERT BEFORE .text;\n')
 print('selected',len(selected),'rounded bytes',used,'training PC hits',[sum(c[n] for n in selected) for c in hits],flush=True)
