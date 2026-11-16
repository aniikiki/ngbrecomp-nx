"""Compare CPU for the same FIFO positions, with and without exact draw-signature matching."""
from pathlib import Path
from statistics import mean,median
import sys
prefix,a,b=sys.argv[1:]
p=Path('build/switch-runtime/core-perf')/('opening-rng-correspondence' if prefix in ('stack-inner-span','sched-one','lane-one','retpg-one','maskpkt-one','extrapg-one','indexbatch-one','cumulative-one') else 'opening-present-combined')
for i in (1,2):
 def read(arm):
  s=(p/f'{prefix}-{arm}-{i}.log').read_text()
  assert 'reason=verified 120 original demo frames' in s
  r={}
  for line in s.splitlines():
   v=line.split()
   if v[:1]==['[PRESENT_MIX]'] and int(v[1])+1==int(v[2]) and 1<=int(v[2])<120:
    k=int(v[2]);assert k not in r;r[k]=(v[3:6],int(v[6])/1e6)
  assert len(r)==119
  if prefix in ('stack-inner-span','sched-one','lane-one','retpg-one','maskpkt-one','extrapg-one','indexbatch-one','cumulative-one'):
   rng={int(v[1]):tuple(v[-2:]) for line in s.splitlines() if (v:=line.split()) and v[0]=='[RNG_PRESENT]' and v[2]=='1'}
   assert r.keys()<=rng.keys()
   r={k:((geometry,rng[k]),t) for k,(geometry,t) in r.items()}
  return r
 x,y=read(a),read(b)
 for lo,hi in [(1,30),(31,119),(1,119)]:
  keys=list(range(lo,hi+1));same=[k for k in keys if x[k][0]==y[k][0]]
  d=lambda k:x[k][1]-y[k][1]
  print(i,lo,hi,len(same),'matched; saved host ms all / matched mean / matched median:',*[round(n,5) for n in [mean(map(d,keys)),mean(map(d,same)),median(map(d,same))]] if same else [round(mean(map(d,keys)),5),None,None])
