"""Screen before building: require >=70% page samples inside the live range in each late-window run."""
from pathlib import Path
import runpy,contextlib,io,re
f=io.StringIO()
with contextlib.redirect_stdout(f):runpy.run_path(str(Path(__file__).with_name('low-prefix-report.py')))
import ast
vals=[]
for l in f.getvalue().splitlines():
 m=re.match(r'(\d+) 31 120 (\{.*?\}) prefix endpoints',l)
 if m:
  counts=ast.literal_eval(m[2]);n=sum(counts.values())
  vals.append((n,n-counts.get('outside',0)))
assert len(vals)==2
print('late low-prefix sample coverage',vals)
if not all(n>=25 and 10*covered>=7*n for n,covered in vals):raise SystemExit('insufficient coverage for a new replay pair')
