"""No FPS from instrumented or seed-controlled runs. Only compare workload repeatability."""
from pathlib import Path
import runpy,re
d=Path('build/switch-runtime/core-perf/opening-rng-correspondence')
q=runpy.run_path(str(Path(__file__).with_name('present-mix-report.py')))
q['read'].__globals__['d']=d
for arm in ['natural','fixed']:
 rr=[]
 for n in [1,2]:
  name=f'{arm}-{n}';p=d/(name+'.log')
  if not p.exists():continue
  s=p.read_text();assert 'verified 120 original demo frames' in s
  rng=[(int(f),int(mode),int(seeds),int(last),int(tot),int(count),h) for f,mode,seeds,last,tot,count,h in re.findall(r'^\[RNG_PRESENT\] (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\w+)$',s,re.M)]
  assert rng and all(r[1]==(arm=='fixed') for r in rng)
  print(name,'seed calls by final observed Present',rng[-1][2],'last original seed',rng[-1][3],'rand calls in late Present windows',sum(r[5] for r in rng if 30<r[0]<120))
  rows=q['read'](name)
  # pm_present prints its first raw observation without a complete interval.
  late=[r for prev,r in zip(rng,rng[1:]) if prev[0]>=30 and r[0]<120]
  assert len(late)==len(rows) and all(r[0]==x[1] for r,x in zip(late,rows))
  rr.append((rows,late))
 if len(rr)==2:
  (a,x),(b,y)=rr
  geom=q['matching'](a,b)
  print(arm,'ordered geometry matches',len(geom),'of',len(a),len(b),'with identical count/hash of rand output',sum(x[i][5:]==y[j][5:] for i,j in geom))
