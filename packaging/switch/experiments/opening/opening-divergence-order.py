"""Compare first observed mismatches by ordinal, including unchanged-build repeat controls."""
import contextlib,io,runpy
from pathlib import Path
with contextlib.redirect_stdout(io.StringIO()):
    runs=runpy.run_path(str(Path(__file__).with_name('cadence-work-holdout.py')))['runs']
def compare(a,b):
    xy=list(zip(a,b))
    def first(sl):
        return next((i for i,(x,y) in enumerate(xy,1) if x[2][sl]!=y[2][sl]),None)
    g,r=first(slice(0,3)),first(slice(3,5))
    print('geometry/RNG first',g,r,'of',len(xy),'draw count/volume/order hash first',
          *[first(i) for i in range(3)])
    for i in sorted({v for v in (g,r) if v is not None}):
        x,y=xy[i-1]
        print(' ordinal',i,'FIFO ends',x[1],y[1],'draws/volume',x[2][:2],y[2][:2],
              'RNG counts',x[2][3],y[2][3])
for name,group in [('ordinary',runs[:4]),('paced',runs[4:])]:
    for label,a,b in [('pair1',0,1),('pair2',2,3),('baseline repeat',0,2),('candidate repeat',1,3)]:
        print(name,label);compare(group[a],group[b])
