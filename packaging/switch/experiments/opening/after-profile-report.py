"""Classify exclusively by the interrupted PC; do not ascribe callees to sampled LR."""
import re,bisect,sys
from pathlib import Path
from collections import Counter
d=Path('build/switch-runtime/core-perf')/('opening-copy-profile' if '--copy' in sys.argv else 'opening-compact-profile' if '--compact' in sys.argv else 'opening-after-profile')
sym={}
for l in (d/'symbols.txt').read_text().splitlines():
 a,n,_,fn=l.split(maxsplit=3);a,n=int(a,16),int(n,16)
 if n>sym.get(a,(0,''))[0]:sym[a]=(n,fn)
keys=sorted(sym)
for lo,hi in ([(1,1),(2,4),(5,30),(31,120)] if '--split-start' in sys.argv else [(1,30),(31,120)]):
 counts=Counter();rank=Counter()
 for i in range(1,5):
  s=(d/f'run-{i}.log').read_text();assert 'reason=verified 120 original demo frames' in s
  mods={(f,pc):(Path(m).name,fn) for f,pc,m,fn in re.findall(r'^\[FRAME_MODULE\] (\d+) (\w+) \w+ (\S+) (\S+)$',s,re.M)}
  rows=re.findall(r'^\[FRAME_PC\] (\d+) (\w+)$',s,re.M)
  delivered,lost=map(int,re.search(r'\[FRAME_PC_COUNT\] (\d+) (\d+)',s).groups());assert delivered==len(rows)
  c=Counter()
  for f,pc in rows:
   if not lo<=int(f)<=hi:continue
   addr=int(pc,16);j=bisect.bisect_right(keys,addr)-1;fn='';module,other=mods.get((f,pc),('?','?'))
   if j>=0:
    a=keys[j];n,name=sym[a]
    if addr<a+n:fn=name
   if fn.startswith(('ngb_reg_sub_','ngb_reg_d3d_orig_')):group='generated guest'
   elif fn.startswith(('ngb_gate_','ngb_reg_checkpoint')):group='ABI gates/checkpoint'
   elif not fn:group=module
   else:group='other executable'
   c[group]+=1;rank[fn or module+':'+other]+=1
  counts.update(c);print(lo,hi,'run',i,'whole-window missed',lost,'samples',sum(c.values()),dict(c))
 print(lo,hi,'pooled',counts,'top exclusive PCs by function',rank.most_common(18))
