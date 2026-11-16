"""Count distinct interrupt samples (not inclusive call counts) in the 0.51 opening."""
from pathlib import Path
from collections import Counter
import json,re,runpy
base=Path('build/switch-runtime')
release=base/'history/0.51.0-rc1'
dep=json.loads((release/'deployment.json').read_text())
api=runpy.run_path(str(Path(__file__).resolve().parents[2]/'analyze-profile.py'))
sym=api['load_symbols'](release/'symbols.gz')
rows=api['parse_windows']((base/dep['hardware_log']).read_text().splitlines())[1,120]['profiles']['guest'][1]
lines=(base/'core-perf/opening-setup/leaf-budget.tsv').read_text().splitlines()
assert bytes.fromhex(lines[0].split()[3])==(release/'ngb-startup.nro').open('rb').read(84)[64:84]
leaf=[x.split('\t') for x in lines if re.match(r'^\d+\t',x)]
rows=[r for r in rows if 1<=r[0]<=120];assert len(rows)==len(leaf)==307
names=dict(re.findall(r'void sub_([0-9A-F]+)\(void\)\s+/\* (\w+) \*/',Path('src/d3d/d3d_hooks.c').read_text()))
for first in (1,2):
 groups=Counter(); original=Counter();memory=Counter();total=0
 for row,rec in zip(rows,leaf):
  f,worker,_,_,_,pcs=row
  assert (f,worker,pcs[0])==(int(rec[0]),int(rec[1]),int(rec[2],16))
  if f<first:continue
  total+=1
  s=[sym(p).removeprefix('ngb_reg_').split('.localalias')[0] for p in pcs]
  sdk=next((v[9:] for v in s if v.startswith('d3d_orig_')),None)
  service=any(v in {'execute_dma','service_dma','submit_dma','ngb_poll_due','yield_worker','poll_callbacks'} for v in s)
  host=any(v in {'d3d_hook','d3d_after','d3d_hle_call','d3d_hle_after'} for v in s)
  k='runtime service' if service else 'native graphics hook' if host else 'original graphics library' if sdk else 'remaining'
  groups[k]+=1
  if sdk and k=='original graphics library':original[names.get(sdk,sdk)]+=1
  if rec[4] in {'guest page-table load','guest RAM alias translation','guest memory header (debug line)','memory helper'}:memory[k]+=1
 print(first,120,total,groups,memory,original.most_common(15))
