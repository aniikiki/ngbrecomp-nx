"""Rank coherent game-thread pre-Draw families. Fixed sampling probability, no double attribution."""
from pathlib import Path
import re
from collections import Counter
d=Path('build/switch-runtime/core-perf/opening-mesh-recipe-census')
s=(d/'rank-clock-fields-budget.log').read_text();assert 'verified 120 original demo frames' in s
rows=[(int(pc,16),*map(int,tail.split())) for pc,tail in re.findall(r'^\[RECIPE_RANK\] (\w+) (.*)$',s,re.M)]
assert rows and len({tuple(r[:4]) for r in rows})==len(rows)
for group in range(3):
    expect=tuple(map(int,re.findall(r'^\[RECIPE_PRE\] '+str(group)+r' (\d+) (\d+) (\d+)$',s,re.M)[-1]))
    assert tuple(sum(r[i] for r in rows if r[3]==group) for i in (4,5,6))==expect
print('late draws',sum(r[4] for r in rows),'samples',sum(r[5] for r in rows))
for g in (None,2):
  counts=Counter();samples=Counter();ns=Counter()
  for pc,prog,mask,group,c,n,t in rows:
    if g not in (None,group):continue
    key=(pc,prog) if g is None else (pc,prog,mask);counts[key]+=c;samples[key]+=n;ns[key]+=t
  for k,t in ns.most_common(5):
    print('all' if g is None else 'nonmatching',hex(k[0]),*k[1:],counts[k],samples[k],'sampled share',round(t/ns.total(),3),'us/sample',round(t/samples[k]/1000,3))
