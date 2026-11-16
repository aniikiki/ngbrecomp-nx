from pathlib import Path
from collections import Counter
import re,bisect
d=Path('build/switch-runtime/core-perf/opening-page-operands')
syms={}
for l in (d/'symbols.txt').read_text().splitlines():
 a,n,_,fn=l.split(maxsplit=3);a,n=int(a,16),int(n,16)
 if n>syms.get(a,(0,''))[0]:syms[a]=(n,fn)
keys=sorted(syms)
for i in (1,2):
 s=(d/f'run-{i}.log').read_text();assert 'reason=verified 120 original demo frames' in s
 for lo,hi in [(1,30),(31,120)]:
  counts=Counter();pages=Counter()
  for f,pc,pg in re.findall(r'^\[PAGE_PC\] (\d+) (\w+) (\w+)$',s,re.M):
   if not lo<=int(f)<=hi:continue
   pc,pg=int(pc,16),int(pg,16);j=bisect.bisect_right(keys,pc)-1
   if j<0:continue
   a=keys[j];n,fn=syms[a]
   if pc>=a+n or not fn.startswith(('ngb_reg_sub_','ngb_reg_d3d_orig_')):continue
   counts['static low' if 8<=pg<0x1000 else 'VM' if 0x1000<=pg<0x3e00 else 'upper 2MiB low RAM' if 0x3e00<=pg<0x4000 else 'upper alias' if pg>=0x80000 else 'other']+=1
   pages[pg]+=1
  print(i,lo,hi,sum(counts.values()),counts,'top pages',pages.most_common(8))
