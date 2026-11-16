"""Attribute the two outer update callsites without charging nested IRQ/service as game work."""
from collections import Counter
from pathlib import Path
import sys,runpy
api=runpy.run_path(str(Path(__file__).resolve().parents[2]/'analyze-profile.py'))
sym=api['load_symbols'](sys.argv[2])
rows=api['parse_windows'](Path(sys.argv[1]).read_text().splitlines())[1,120]['profiles']['guest'][1]
for site in [0x2213b8,0x1e99554]:
    leaves=Counter(); branches=Counter()
    for f,_,_,_,_,pcs in rows:
        if not 1<=f<=120 or site not in pcs:continue
        st=[sym(p).removeprefix('ngb_reg_').split('.localalias')[0] for p in pcs[:pcs.index(site)]]
        if any(x in {'ngb_poll_due','execute_dma','service_dma','yield_worker','poll_callbacks'} for x in st):
            branches['runtime service']+=1
        else:
            ordered=list(dict.fromkeys(s for s in reversed(st) if s.startswith('sub_')))
            branches[tuple(ordered[:2])]+=1
        leaves[st[0]]+=1
    print(hex(site),sum(leaves.values()),branches)
