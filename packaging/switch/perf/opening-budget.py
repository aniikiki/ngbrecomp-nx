"""Report only scene flips 1..120. Do not infer removable CPU time from samples."""
from pathlib import Path
import math,runpy,statistics as st,sys
api=runpy.run_path(str(Path(__file__).resolve().parents[1]/'analyze-profile.py'))
w=api['parse_windows'](Path(sys.argv[1]).read_text().splitlines())[(1,120)]
rows=w['cpu'];assert [r[0] for r in rows]==list(range(1,121)) and all(r[3]==0 for r in rows)
for lo,hi in ((1,120),(1,30),(31,60),(61,90),(91,120)):
 r=rows[lo-1:hi];wall=[x[1]/1000 for x in r];cpu=[x[2]/1000 for x in r]
 print(f'{lo}-{hi}: wall {st.mean(wall):.2f}, P95 {sorted(wall)[math.ceil(len(r)*.95)-1]:.2f}, main CPU {st.mean(cpu):.2f} ms; draws {st.mean(x[4] for x in r):.1f}; over budget {sum(t>1000/60 for t in wall)}/{len(r)}')
sym=api['load_symbols'](sys.argv[2]);from collections import Counter
c=Counter()
for f,_,_,_,_,pcs in w['profiles']['guest'][1]:
 if not 1<=f<=120:continue
 stack=[sym(pc).removeprefix('ngb_reg_').split('.localalias')[0] for pc in pcs]
 if 'sub_001CA790' in stack:
  where=next((p for p in stack if p in {'sub_001CB260','sub_001CB3B0','sub_001CB510','sub_001CB550'}),'other callback or list')
  c[where]+=1
print('ordered-list samples by callback',dict(c))
