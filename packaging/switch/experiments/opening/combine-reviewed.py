"""Choose independent code+placement candidates using completed natural-opening
runs, then remeasure the actual combination. Never add individual savings."""
from pathlib import Path
from statistics import mean
import sys,re
base=Path('build/switch-runtime/core-perf/wide-start')
def score(tag):
 pairs=[]
 for i in range(1,5):
  stats=[]
  for arm in ('original','limit'):
   p=base/f'{tag}-{arm}-{i}.log'
   if not p.exists():return
   s=p.read_text()
   if '[RESULT] status=1 reason=verified 120 original demo frames' not in s:return
   a=[tuple(map(int,r)) for r in re.findall(r'^\[OPEN_PAIR\] (\d+) \d+ (\d+) (\d+)$',s,re.M)]
   if [r[0] for r in a]!=list(range(1,121)):return
   stats.append(tuple(mean(r[k] for r in a[30:]) for k in (1,2)))
  (at,ad),(bt,bd)=stats
  if not .97<bd/ad<1.03:return
  pairs.append(1-bt/at)
 if min(pairs)>0 and mean(pairs)>.015:return mean(pairs)
if __name__=='__main__':
 # Layout resolution is tied to the original object names; audit actual final
 # addresses in wide-motion.py. Read-only floating folds remain diagnostic-only.
 layout=score('hot-layout')
 options={t:score(t) for t in ('page-limit','register-ticket','compact','region-bias','stack-leaves','icall-direct')}
 print('repeatable candidate fractions',options,'layout',layout,file=sys.stderr)
 valid=[k for k,v in options.items() if v]
 if layout and valid:print('--'+max(valid,key=options.get),'--hot-layout')
