"""Test ordinal drift without consulting timings or selecting favorable offsets."""
from collections import Counter
from functools import reduce
from pathlib import Path
import runpy,contextlib,io
with contextlib.redirect_stdout(io.StringIO()):
    runs=runpy.run_path(str(Path(__file__).with_name('cadence-work-holdout.py')))['runs']
tails=[[r for r in run if 91<=r[1]<120] for run in runs]
print('tail counts',list(map(len,tails)))
# Also allow every observed ordinal in other arms, so an offset at the window
# boundary cannot make an actually shared signature appear absent.
for name,key in [('geometry',lambda r:r[2][:3]),('interval RNG count',lambda r:r[2][3]),('per-Present RNG hash',lambda r:r[2][4]),('joint',lambda r:r[2])]:
    def shared(arr):return sum(reduce(lambda a,b:a&b,(Counter(map(key,rs)) for rs in arr)).values())
    same=sum(all(key(r)==key(g[0]) for r in g) for g in zip(*runs) if 91<=g[0][1]<120)
    print(name,'same ordinal / any order within tail / baseline tail vs entire other runs',
          same,shared(tails),shared([tails[0],*runs[1:]]))
for i,(a,b) in enumerate(zip(runs[::2],runs[1::2])):
    g=[(x,y) for x,y in zip(a,b) if 91<=x[1]<120 and 91<=y[1]<120]
    m=[(x,y) for x,y in g if x[2]==y[2]]
    w=[(x,y) for x,y in m if all(abs(x[k]-y[k])<=max(1,x[k])*.025 for k in (4,5))]
    print('pair',i+1,'overlap/matched/work-matched',len(g),len(m),len(w),
          'CPU old minus new ms',round(sum(x[3]-y[3] for x,y in w)/len(w)/1e6,4) if w else None)
    if not m:
        # Count-only matching does not guarantee identical random values.
        first=next(((j,x[1],y[1],x[2][3],y[2][3]) for j,(x,y) in enumerate(zip(a,b),1)
                    if x[2][4]!=y[2][4]),None)
        print('first per-Present RNG mismatch (ordinal/FIFO ends/interval counts)',first)
        print('tail geometry / RNG count / RNG hash same ordinal',
              *(sum(x[2][k]==y[2][k] for x,y in g) for k in (slice(0,3),3,4)))
