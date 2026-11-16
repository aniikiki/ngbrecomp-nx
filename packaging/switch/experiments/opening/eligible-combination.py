"""Choose only orthogonal winners from balanced natural-opening replays.
Hold the selected combination out and time its real execution; never add gains."""
from pathlib import Path
from statistics import mean
import re,sys
d=Path('build/switch-runtime/core-perf/wide-start')
groups=[
 ('full-guest','double-entry','vector-registers','packed-ops','opening-speed','page-limit','fuse-hot','register-ticket'),
 ('hle-leaf','d3d-private','live-matrices'),
 ('service-cost',),
]
def score(tag):
 xs=[]
 for i in range(1,5):
  halves=[]
  for arm in ('original','limit'):
   f=d/f'{tag}-{arm}-{i}.log'
   if not f.is_file():return
   s=f.read_text()
   if '[RESULT] status=1 reason=verified 120 original demo frames' not in s:return
   rr=[tuple(map(int,r)) for r in re.findall(r'^\[OPEN_PAIR\] (\d+) \d+ (\d+) (\d+)$',s,re.M)]
   if [r[0] for r in rr]!=list(range(1,121)):return
   halves.append([sum(x[k] for x in rr[start:]) for start in (0,30) for k in (1,2)])
  a,b=halves
  if any(not .965<b[j]/a[j]<1.035 for j in (1,3)):return
  xs.append((1-b[0]/a[0],1-b[2]/a[2]))
 if min(x[1] for x in xs)<=0 or mean(x[0] for x in xs)<=0:return
 v=mean(x[1] for x in xs)
 if v>.012:return v
def choose():
 result=[]
 for group in groups:
  good=[(v,t) for t in group if (v:=score(t))]
  if good:result.append(max(good)[1])
 # Gate observers must be built from the same ABI; HLE and live-matrix both
 # replace hle.cpp. Skip a gate experiment if the register domain also changes.
 if any(x in result for x in ('hle-leaf','d3d-private')) and any(x in result for x in groups[0]):
  result=[x for x in result if x not in ('hle-leaf','d3d-private')]
 return result
if __name__=='__main__':
 chosen=choose()
 print('eligible independent variants: '+str(chosen),file=sys.stderr)
 if len(chosen)>1:print(' '.join('--'+t for t in chosen))
