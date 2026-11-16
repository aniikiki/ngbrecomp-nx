"""Compare peer-run variability before attributing pixel differences to prewarming."""
from pathlib import Path
import re,itertools
d=Path('build/switch-runtime/core-perf/opening-present-combined')
runs={}
for name in ['ref-0','base-1','warm-1','warm-2']:
 s=(d/f'recipediff-{name}.log').read_text();assert 'verified 120 original demo frames' in s and '[IDLE_DEVICE] adopted at scene start' in s
 rows=re.findall(r'^\[OPEN_PIXELS\] (\d+) (\w+)$',s,re.M)
 assert [int(i) for i,_ in rows]==list(range(120)),(name,len(rows))
 runs[name]=[h for _,h in rows]
 if name!='ref-0':
  delta=re.findall(r'^\[PIXEL_DIFF\] (\d+) rgb=(\d+) alpha=(\d+) peak=(\d+)$',s,re.M)
  assert [int(x[0]) for x in delta]==[15,76,77,78,79]
  print(name,'vs ref: frame / differing RGB pixels / differing alpha / peak RGB channel error',delta)
for a,b in itertools.combinations(runs,2):
 diff=[i+1 for i,(x,y) in enumerate(zip(runs[a],runs[b])) if x!=y];print(a,b,'different scans',diff)
only=[i+1 for i,(a,b,c,e) in enumerate(zip(*runs.values())) if a==b and c==e and a!=c]
print('repeated difference isolated to setting in this sample',only)
