"""Estimate coverage of a single range. Flip snapshots are not validity proofs between flips."""
from pathlib import Path
import re
s=Path('build/switch-runtime/core-perf/opening-stack-window/budget.log').read_text()
assert 'verified 120 original demo frames' in s
for f,n in [(30,30),(120,90)]:
 pages={int(i):tuple(map(int,(a,b,c,d))) for i,a,b,c,d in re.findall(r'^\[SW_PAGE\] '+str(f)+r' (\d+) (\d+) (\d+) (\d+) (\d+)$',s,re.M)}
 counts=dict((int(i),int(h)) for i,h in re.findall(r'^\[SW_FULL\] '+str(f)+r' (\d+) (\d+)$',s,re.M))
 assert set(counts)==set(range(128)) and re.search(r'^\[SW_MAP\] '+str(f)+' '+str(n)+' ',s,re.M)
 allops=sum(map(sum,pages.values()));assert allops>0
 runs=[];start=None
 for i in range(129):
  if counts.get(i)==n:
   if start is None:start=i
  elif start is not None:
   covered=sum(sum(pages.get(j,(0,0,0,0))[:2]) for j in range(start,i))
   runs.append((covered,start,i));start=None
 best=max(runs,default=(0,0,0))
 print(f,'accesses/frame',round(allops/n,1),'outside/frame',round(sum(pages.get(128,()))/n,1),'best at snapshots',hex((0x1180+best[1])<<12),hex((0x1180+best[2])<<12),f'{best[0]/allops:.2%}', 'baseline fast accesses/frame',round(best[0]/n,1))
