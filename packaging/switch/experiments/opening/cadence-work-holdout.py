"""Match whole-scene Present ordinal and both signatures before comparing work or CPU."""
from pathlib import Path
from statistics import mean
import re
d=Path('build/switch-runtime/core-perf/opening-rng-correspondence')
def load(tag,arm):
    s=(d/f'{tag}-{arm}.log').read_text()
    assert 'reason=verified 120 original demo frames' in s
    paced=tag=='paced-cumulative'
    sleeps=re.findall(r'^\[DRAW_CADENCE\] (\d+) (\d+) (\d+)$',s,re.M)
    assert (bool(sleeps)==paced)
    if paced:
        assert [int(f) for f,_,_ in sleeps]==list(range(31,121)) and sum(int(v) for _,_,v in sleeps)>0
    rows=[];rng=None
    for line in s.splitlines():
        x=line.split()
        if x[:1]==['[RNG_PRESENT]']:rng=x
        if x[:1]==['[PRESENT_MIX]']:
            assert rng and x[2]==rng[1] and rng[2]=='1'
            rows.append((int(x[1]),int(x[2]),tuple(x[3:6]+rng[-2:]),*map(int,x[6:9])))
            rng=None
    assert rows and rows[0][0]==0 and all(a[1]==b[0] for a,b in zip(rows,rows[1:]))
    return rows
runs=[load(tag,arm) for tag in ('cumulative-one','paced-cumulative')
      for arm in ('original-1','split-1','original-2','split-2')]
eligible=[g for g in zip(*runs) if all(30<=r[0]<=r[1]<120 for r in g)]
matched=[g for g in eligible if all(r[2]==g[0][2] for r in g)]
print('aligned ordinals in window',len(eligible),'geometry + RNG matched',len(matched))
for tol in (None,.025,.01):
    # Check counts both within each optimization pair and across cadence regimes.
    pairs=[(0,1),(2,3),(4,5),(6,7),(0,4),(1,5),(2,6),(3,7)]
    cohort=[g for g in matched if tol is None or all(abs(g[a][k]-g[b][k])<=tol*max(1,g[a][k]) for a,b in pairs for k in (4,5))]
    print('work tolerance',tol,'n',len(cohort))
    if cohort:
        print('baseline FIFO end bins <=60 / <=90 / later',*[sum(lo<=g[0][1]<hi for g in cohort) for lo,hi in ((30,61),(61,91),(91,120))])
        for a,b in pairs[:4]:
            print(a,b,'CPU saved ms',round(mean((g[a][3]-g[b][3])/1e6 for g in cohort),4))
if matched:
    for a,b in [(0,4),(2,6)]:
        print('baseline paced minus normal, entries/polls per interval',*[round(mean(g[b][k]-g[a][k] for g in matched),1) for k in (4,5)])
