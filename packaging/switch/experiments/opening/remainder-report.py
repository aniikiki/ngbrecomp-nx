"""Reconcile the 0.51 true timed subtotal and all saved outside-scope samples."""
from pathlib import Path
from collections import Counter
import re,json,runpy
base=Path('build/switch-runtime');rel=base/'history/0.51.0-rc1'
a=runpy.run_path(str(Path(__file__).resolve().parents[2]/'analyze-profile.py'))
sym=a['load_symbols'](rel/'symbols.gz')
log=(base/json.loads((rel/'deployment.json').read_text())['hardware_log']).read_text()
end=log.index('[SERVICE] 3D scene flips=120 ')
def delta(pattern):
 r=re.findall(pattern,log[:end]);assert len(r)==2;return [int(b)-int(a) for a,b in zip(*r)]
nf,index,mesh,other=delta(r'sampled_frames=(\d+) indexed_us=(\d+) mesh_excluding_index_us=(\d+) remaining_us=(\d+)')
_,material=delta(r'sampled material setters in_mesh_us=(\d+) outside_mesh_us=(\d+)')
frames=[i for i in range(31,121) if (i-1)%16 == (9*((i-1)//16))%16]
assert len(frames)==nf
print(frames, 'wall us per timed frame: remainder/material/other',*[v/nf for v in (other,material,other-material)])
rows=a['parse_windows'](log.splitlines())[1,120]['profiles']['guest'][1]
for subset in [frames, list(range(31,121))]:
 groups=Counter();br=Counter(); residual=[]
 for f,worker,sc,_,_,pcs in rows:
  if f not in subset or sc&3:continue
  st=[sym(pc).removeprefix('ngb_reg_').split('.localalias')[0] for pc in pcs]
  roots=['sub_000320E0','sub_001CB9A0','sub_001CA790']
  task=next((v for v in st if v in roots),None)
  if not task and 'sub_0030C8B0' in st:task=next((v for v in reversed(st[:st.index('sub_0030C8B0')]) if v.startswith('sub_')),None)
  task=task or 'unresolved'
  groups[task]+=1
  branch=next((v for v in st if v in {'sub_001CC5A0','sub_001CBA70','sub_001CC300','sub_0001FB60','sub_00020040','sub_001CB3B0','sub_001CB510','sub_001CB550','sub_001CB260'}),'other')
  br[task,branch]+=1
  if task=='unresolved':residual.append(st[0])
 print(len(subset),'frames:',sum(groups.values()),groups,br,Counter(residual))
