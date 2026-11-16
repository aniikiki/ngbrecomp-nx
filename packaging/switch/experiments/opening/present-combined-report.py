"""Balanced three-arm contrast; strict sequence and coarse shared-work sensitivity."""
from pathlib import Path
from collections import defaultdict
from statistics import mean,median
import re,runpy
d=Path('build/switch-runtime/core-perf/opening-present-combined')
q=runpy.run_path(str(Path(__file__).with_name('present-mix-report.py')))
read=q['read'];read.__globals__['d']=d
arms=('base','retained','combined')
rows={}
for arm in arms:
 for i in range(1,4):
  text=(d/f'{arm}-{i}.log').read_text()
  assert list(map(int,re.findall(r'^\[OPEN_PAIR\] (\d+) ',text,re.M)))==list(range(1,121))
  rows[arm,i]=read(f'{arm}-{i}')
def strata(r):
 bins=defaultdict(list)
 for a,b,draws,vertices,sig,ns,entries,polls in r:
  bins[(b//15,draws//16,entries//2048,polls//8192)].append(ns/1e6)
 return bins
for left,right in [('base','combined'),('retained','combined')]:
 for i in range(1,4):
  a,b=rows[left,i],rows[right,i]
  sig=q['matching'](a,b)
  x,y=strata(a),strata(b)
  common=x.keys()&y.keys()
  pairs=sum(min(len(x[k]),len(y[k])) for k in common)
  coarse=sum((mean(x[k])-mean(y[k]))*min(len(x[k]),len(y[k])) for k in common)/pairs if pairs else None
  print(left,right,i,'presents',len(a),len(b),'raw ms saved',round((mean(r[5] for r in a)-mean(r[5] for r in b))/1e6,4),
    'identical geometry',len(sig),'median ms saved',round(median((a[k][5]-b[j][5])/1e6 for k,j in sig),4) if sig else None,
    'shared-work coverage',pairs,'coarse ms saved',round(coarse,4) if pairs else None)
