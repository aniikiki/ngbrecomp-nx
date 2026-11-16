"""Opening CPU per unit of work, as a sensitivity check alongside raw A/B.
No fitting to device results. Fit the baseline slope on reference runs only,
with centered frame and run fixed effects. Report candidate change both ways."""
from pathlib import Path
import sys,re
from statistics import mean
def invert(a,b):
 for j in range(len(b)):
  k=max(range(j,len(b)),key=lambda i:abs(a[i][j]))
  if abs(a[k][j])<1e-9:raise ValueError('singular work features')
  a[j],a[k]=a[k],a[j];b[j],b[k]=b[k],b[j]
  z=a[j][j];a[j]=[v/z for v in a[j]];b[j]/=z
  for i in range(len(b)):
   if i==j:continue
   z=a[i][j];b[i]-=z*b[j];a[i]=[u-z*v for u,v in zip(a[i],a[j])]
 return b
d=Path(sys.argv[1]);tag=sys.argv[2];runs={}
for arm in ('original','limit'):
 for i in range(1,5):
  s=(d/f'{tag}-{arm}-{i}.log').read_text()
  assert '[RESULT] status=1 reason=verified 120 original demo frames' in s
  t={int(f):(int(n)/1e6,int(dr)) for f,n,dr in re.findall(r'^\[OPEN_PAIR\] (\d+) \d+ (\d+) (\d+)$',s,re.M)}
  w={int(f):(int(e)/1000,int(p)/1000) for f,e,p in re.findall(r'^\[OPEN_WORK\] (\d+) (\d+) (\d+)$',s,re.M)}
  assert sorted(t)==sorted(w)==list(range(1,121))
  runs[arm,i]=[(*t[f],*w[f]) for f in range(31,121)]
x=[runs['original',i] for i in range(1,5)]
grand=[mean(v[j] for r in x for v in r) for j in range(4)]
rows=[]
for r in x:
 avg=[mean(v[j] for v in r) for j in range(4)]
 for f,v in enumerate(r):rows.append([v[j]-avg[j]-mean(rr[f][j] for rr in x)+grand[j] for j in range(4)])
coef=invert([[sum(v[j]*v[k] for v in rows) for k in (1,2,3)] for j in (1,2,3)],[sum(v[j]*v[0] for v in rows) for j in (1,2,3)])
print('baseline slopes: ms/draw, ms/1000 entries, ms/1000 polls',coef)
for i in range(1,5):
 dif=[mean(a[j]-b[j] for a,b in zip(runs['original',i],runs['limit',i])) for j in range(4)]
 print(i,'raw ms saved',round(dif[0],4),'adjusted',round(dif[0]-sum(c*v for c,v in zip(coef,dif[1:])),4),'work deltas',*[round(v,3) for v in dif[1:]])
