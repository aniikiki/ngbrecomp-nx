"""Use geometry, entries and poll counts only to choose cohorts; no timing-based selection."""
from pathlib import Path
from statistics import mean, median
import contextlib,io,runpy
with contextlib.redirect_stdout(io.StringIO()):
 rows=runpy.run_path(str(Path(__file__).with_name('joint-common-frames.py')))['same']
def mismatch(r):
 return max(abs(r[k][4][j]-r[k+1][4][j])/max(1,r[k][4][j]) for k in (0,2) for j in (0,1))
for tol in (.001,.0025,.005,.01,.025,1):
 subset=[r for r in rows if mismatch(r)<=tol]
 if not subset:print(tol,'empty');continue
 print('relative tolerance',tol,'count',len(subset),'phase counts',[sum(lo<=r[0][1]<lo+30 for r in subset) for lo in (31,61,91)])
 print('A/B mean saves',*[round(mean(r[k][3]-r[k+1][3] for r in subset),4) for k in (0,2)],'baseline and candidate repeat shifts',*[round(mean(r[k+2][3]-r[k][3] for r in subset),4) for k in (0,1)])
 print('both faster',sum(all(r[k][3]>r[k+1][3] for k in (0,2)) for r in subset),'of',len(subset))
