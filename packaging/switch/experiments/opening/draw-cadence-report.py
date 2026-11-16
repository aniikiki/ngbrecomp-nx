"""Verify same ELF, complete flip records and that the intended time perturbation ran."""
import re
from pathlib import Path
from statistics import mean,median
d=Path('build/switch-runtime/core-perf/opening-draw-correspondence')
for arm in ('normal','paced'):
 s=(d/(arm+'.log')).read_text();assert 'verified 120 original demo frames' in s
 def rows(tag):
  return [tuple(map(int,x.split())) for x in re.findall(r'^\['+tag+r'\] ([0-9 ]+)$',s,re.M)]
 co=rows('DRAW_CORRESPOND');sw=rows('SWAP_SLICE');cd=rows('DRAW_CADENCE')
 assert [r[0] for r in co]==[r[0] for r in sw]==list(range(1,121))
 assert [r[0] for r in cd]==list(range(31,121))
 assert [r[2] for r in sw]==[r[1] for r in co]
 calls=sum(r[1] for r in cd);sleeps=sum(r[2] for r in cd)
 assert calls and (sleeps>0)==(arm=='paced'),(arm,calls,sleeps)
 a=co[30:];print(arm,'service checks/sleeps',calls,sleeps,'HLE range',min(x[1] for x in a),max(x[1] for x in a),'median |END-HLE|',median(abs(x[1]-x[2]) for x in a),'max',max(abs(x[1]-x[2]) for x in a),'flips with !=1 Swap',sum(x[1]!=1 for x in sw[30:]))
