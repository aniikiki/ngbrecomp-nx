"""Separate first flip CPU and subsequent front-window CPU using aligned FIFO boundaries."""
from pathlib import Path
import re

root=Path('build/switch-runtime/core-perf/opening-present-combined')
for prefix in ('joint','jointbuf'):
    for pair in (1,2):
        runs=[]
        for arm in ('base','next'):
            s=(root/f'{prefix}-{arm}-{pair}.log').read_text()
            assert 'reason=verified 120 original demo frames' in s
            rows=[tuple(map(int,m)) for m in re.findall(r'^\[OPEN_PAIR\] (\d+) \d+ (\d+) (\d+)$',s,re.M)]
            assert [f for f,t,n in rows]==list(range(1,121))
            walls=[int(x) for x in re.findall(r'3D scene flips=(?:30|120) draws=\d+ elapsed_ms=(\d+)',s)]
            assert len(walls)==2
            mix=[line.split()[1:6] for line in s.splitlines() if line.startswith('[PRESENT_MIX] ')]
            assert len(mix)==120
            work=[tuple(map(int,m)) for m in re.findall(r'^\[OPEN_WORK\] (\d+) (\d+) (\d+)$',s,re.M)]
            assert [f for f,e,p in work]==list(range(1,121))
            runs.append((rows,walls,mix,work))
        (a,aw,am,ax),(b,bw,bm,bx)=runs
        print(prefix,pair, 'phase, wall saved ms/window, thread CPU saved ms/window, FIFO draw totals A/B')
        for l,r,wall in [(0,30,aw[0]-bw[0]),(30,120,(aw[1]-aw[0])-(bw[1]-bw[0]))]:
            print(l+1,r,wall,round(sum(x[1]-y[1] for x,y in zip(a[l:r],b[l:r]))/1e6,2),
                  sum(x[2] for x in a[l:r]),sum(x[2] for x in b[l:r]))
        print('first flip CPU difference ms',round((a[0][1]-b[0][1])/1e6,2),
              'front 30 ordered Present signatures/boundaries matching',sum(x==y for x,y in zip(am[:30],bm[:30])))
        first=(a[0][1]-b[0][1])/1e6
        rest=sum(a[k][1]-b[k][1] for k in range(1,30))/1e6
        print('first share of net front CPU saving', round(first/(first+rest),3),
              'subsequent 29 CPU saving ms/flip',round(rest/29,3),
              'first FIFO draws, entries, polls', (a[0][2],*ax[0][1:]),(b[0][2],*bx[0][1:]),
              'first 30 geometry-only matches',sum(x[2:]==y[2:] for x,y in zip(am[:30],bm[:30])))
