"""Disjoint guest work families; classify services BEFORE assigning title tasks.
Stack includes time in callee; don't charge the enclosing game update for servicing DMA."""
from pathlib import Path
import runpy,re,sys
from collections import Counter
a=runpy.run_path(str(Path(__file__).resolve().parents[1]/'analyze-profile.py'));sym=a['load_symbols'](sys.argv[2])
for (lo,hi),w in a['parse_windows'](Path(sys.argv[1]).read_text().splitlines()).items():
    groups=Counter();by_task=Counter()
    for f,_,_,_,_,pcs in w['profiles']['guest'][1]:
        if not lo<=f<=hi:continue
        labels=[sym(pc).removeprefix('ngb_reg_').split('.localalias')[0] for pc in pcs]
        task=next((x for x in labels if x in {'sub_001CA790','sub_001CB9A0','sub_000320E0','sub_00151150'}),'other')
        family=next((kind for kind,names in (
            ('DMA',{'execute_dma','service_dma','submit_dma'}),
            ('runtime poll/service',{'ngb_poll_due','yield_worker','poll_callbacks'}),
            ('D3D hook',{'d3d_hle_call','d3d_hook','d3d_after'}),
            ('mesh/XDK',{'sub_0030BCA0','sub_003C9B40'}),
            ('other render tree',{'sub_001CA790'}),
        ) if names.intersection(labels)), 'game or other')
        groups[family]+=1;by_task[task,family]+=1
    print(f'{lo}-{hi}: guest wall samples={groups.total()}',dict(groups))
    if lo==1801:
        for k in sorted(set(k for k,_ in by_task)):print(k,dict((g,by_task[k,g]) for g in groups if by_task[k,g]))
