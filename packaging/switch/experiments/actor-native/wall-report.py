"""Report coverage and real elapsed time, including worker joins. Do not turn
Linux software-rendered frame timings into estimated Switch FPS."""
from pathlib import Path
from statistics import mean,median
from collections import Counter
import sys,re
for arg in sys.argv[1:]:
 s=Path(arg).read_text()
 if '[RESULT] status=1 reason=verified original combat window' not in s: raise ValueError('incomplete replay')
 def records(key):
  return [tuple(map(int,m.split())) for m in re.findall(r'^\['+key+r'\] ([0-9 ]+)$',s,re.M)]
 loops=[r for r in records('WAVE_WALL') if 1803<=r[0]<1920]
 print(Path(arg).name, 'published jobs:',sum(x[3] for x in loops),'loop counts:',Counter((r[1],r[3]) for r in loops))
 print('excluding training pair; baseline/variant')
 for key,rs in [('actor wall',loops),('frame wall',records('FRAME_WALL')),('frame CPU',records('PAIR'))]:
  # pair frames 1805/1806 etc. Loop labels name preceding flip; frame
  # labels name ending flip. Drop the entire initial training region.
  first=1804 if key=='actor wall' else 1805
  g={i:[] for i in [0,1]};byframe={r[0]:r for r in rs}
  for lo in range(first,1920,2):
   a,b=byframe[lo],byframe[lo+1]
   if a[1]==b[1]:raise ValueError(f'unbalanced pair {lo}')
   for r in (a,b):g[r[1]].append(r[2]/1e6)
  print(key,'mean ms',*(round(mean(v),3) for v in g.values()),'median ms',*(round(median(v),3) for v in g.values()))
