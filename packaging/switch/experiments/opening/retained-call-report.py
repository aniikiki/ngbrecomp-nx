"""Summarize precise call weights; separate generated calls from helpers and indirect sites."""
from pathlib import Path
from collections import Counter
import re,sys
root=Path('build/switch-runtime');owners={}
for f in (root/'gen').glob('recomp_[0-9][0-9][0-9][0-9].c'):
 for fn in re.findall(r'^void ((?:sub_|d3d_orig_)\w+)\(void\)\s*\{',f.read_text(),re.M):
  assert fn not in owners
  owners[fn]=int(f.stem.split('_')[1])
assert len(owners)>10000
for name in sys.argv[1:]:
 f=root/'core-perf'/name/'call-work.txt'
 lines=f.read_text().splitlines()
 assert lines[0]=='unit caller callee precise_weight positive_sites'
 buckets=Counter();edges=Counter();helpers=Counter();ns=set()
 for line in lines[1:]:
  unit,caller,callee,weight,sites=line.split()
  unit=int(unit);weight=int(weight);ns.add(unit)
  cls=('guest-same-unit' if owners.get(callee)==unit else 'guest-other-unit' if callee in owners else 'indirect' if callee=='(indirect)' else 'checkpoint' if callee=='ngb_checkpoint' else 'guest-public-or-external' if callee.startswith(('sub_','d3d_orig_')) else 'helper')
  buckets[cls]+=weight
  if cls.startswith('guest-'):edges[cls,caller,callee]+=weight
  if cls=='helper':helpers[callee]+=weight
 assert ns=={2,10,16,28,29}
 print(name,'weighted calls (only precise blocks)',buckets)
 print('leading other callees',helpers.most_common(12))
 for cls in ['guest-same-unit','guest-other-unit']:
  print(cls,[(k[1:],n) for k,n in edges.most_common() if k[0]==cls][:8])
