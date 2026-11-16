"""Rank repeatable guest work in two independent pairs, with per-window denominators."""
import bisect,re
from collections import Counter
from pathlib import Path
def analyze(d):
 sy={}
 for line in (d/'symbols.txt').read_text().splitlines():
  a,n,_,fn=line.split(maxsplit=3);a,n=int(a,16),int(n,16)
  if n>sy.get(a,(0,''))[0]:sy[a]=(n,fn)
 keys=sorted(sy)
 def loc(pc):
  i=bisect.bisect_right(keys,pc)-1
  if i>=0:
   a=keys[i];size,name=sy[a]
   if pc<a+size:return name
 result={}
 for lo,hi in ((1,30),(31,120)):
  halves=[Counter(),Counter()];total=[0,0]
  for i in range(4):
   s=(d/f'run-{i+1}.log').read_text()
   assert 'reason=verified 120 original demo frames' in s
   rows=re.findall(r'^\[FRAME_PC\] (\d+) (\w+)$',s,re.M)
   assert len(rows)==int(re.search(r'\[FRAME_PC_COUNT\] (\d+)',s)[1])
   for f,pc in rows:
    if lo<=int(f)<=hi:
     k=i//2;total[k]+=1;n=loc(int(pc,16))
     if n and n.startswith(('ngb_reg_sub_','ngb_reg_d3d_orig_')):halves[k][n]+=1
  result[lo]=halves,total
 return result
if __name__=='__main__':
 import sys
 root=Path('build/switch-runtime/core-perf')
 for variant in (sys.argv[1:] or ['compact','copy']):
  for lo,(h,t) in analyze(root/('opening-'+variant+'-profile')).items():
   ranks=sorted(h[0].keys()&h[1].keys(),key=lambda n:(min(h[0][n]/t[0],h[1][n]/t[1]),h[0][n]+h[1][n],n),reverse=True)
   print(variant,lo,'delivered',t,'guest',list(map(Counter.total,h)),'recurrent top functions',[(n,h[0][n],h[1][n]) for n in ranks[:12]])
