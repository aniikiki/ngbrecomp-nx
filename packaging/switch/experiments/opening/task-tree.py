"""First 120 only: separate guest service inside task stacks before attributing game work."""
import collections
from pathlib import Path
import runpy,sys
api=runpy.run_path(str(Path(__file__).resolve().parents[2]/'analyze-profile.py'))
sym=api['load_symbols'](sys.argv[2])
rows=api['parse_windows'](Path(sys.argv[1]).read_text().splitlines())[1,120]['profiles']['guest'][1]
tasks={'sub_001CA790','sub_001CB9A0','sub_000320E0'}
services={'ngb_poll_due','execute_dma','service_dma','submit_dma','yield_worker','poll_callbacks'}
counts=collections.Counter()
for frame,_,_,_,_,pcs in rows:
    if not 1<=frame<=120:continue
    stack=[sym(pc).removeprefix('ngb_reg_').split('.localalias')[0] for pc in pcs]
    task=next((name for name in stack if name in tasks),'other')
    if services.intersection(stack):branch='runtime service (inclusive)'
    elif task=='other':branch='other'
    else:
        callees=[s for s in reversed(stack[:stack.index(task)]) if s.startswith('sub_') and s!=task]
        if task=='sub_000320E0' and callees[:1]==['sub_000298F0']: callees=callees[1:]
        if task=='sub_001CA790':
            branch=next((s for s in callees if s in {'sub_001CB510','sub_001CB3B0','sub_001CB550','sub_001CB260'}),'list overhead or other')
        else:branch=next(iter(callees),'task itself')
    counts[task,branch]+=1
for key,n in counts.most_common():print(*key,n)
print('total',counts.total())
