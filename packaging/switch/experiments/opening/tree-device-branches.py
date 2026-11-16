"""Exclusive partition of delivered device stacks by the child of the innermost visible tree walker."""
from collections import Counter
from pathlib import Path
import runpy,contextlib,io
with contextlib.redirect_stdout(io.StringIO()):
 d=runpy.run_path(str(Path(__file__).with_name('device-owner-rank.py')))
bins=[Counter() for _ in range(3)]; leaves=Counter()
for f,*_,pcs in d['win']['profiles']['guest'][1]:
 if not 31<=f<=120:continue
 t=[d['sym'](a).replace('ngb_reg_','').split('.')[0] for a in pcs]
 g=[z for z in t if z.startswith('sub_')]
 if 'sub_00308D50' not in g:k='outside visible 308D50'
 else:
  pos=g.index('sub_00308D50')
  k=g[pos-1] if pos else 'no visible child'
  leaves[k,t[0]]+=1
 bins[(f-31)//30][k]+=1
agg=sum(bins,Counter());assert sum(agg.values())==224
for k,n in agg.most_common():
 print(k,n,[b[k] for b in bins],[(z,v) for (p,z),v in leaves.most_common() if p==k][:4])
