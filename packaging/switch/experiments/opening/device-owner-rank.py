"""First visible game routine per interrupted guest stack, not inclusive counts or caller proof."""
from collections import Counter
from pathlib import Path
import json,re,runpy
base=Path('build/switch-runtime'); h=base/'history/0.51.0-rc1'
api=runpy.run_path('packaging/switch/analyze-profile.py')
sym=api['load_symbols'](h/'symbols.gz')
log=base/json.loads((h/'deployment.json').read_text())['hardware_log']
win=api['parse_windows'](log.read_text().splitlines())[1,120]
counts=[Counter() for _ in range(3)]
direct=Counter()
for frame,_,_,_,_,pcs in win['profiles']['guest'][1]:
    if not 31<=frame<=120:continue
    for depth,pc in enumerate(pcs):
        m=re.fullmatch(r'(?:ngb_reg_)?sub_([0-9A-Fa-f]+)(?:\..*)?',sym(pc))
        if m:
            owner=m[1].upper()
            if depth==0:direct[owner]+=1
            break
    else:owner='unassigned'
    counts[(frame-31)//30][owner]+=1
total=sum(counts,Counter())
print('samples by block:',[sum(c.values()) for c in counts])
for k,n in total.most_common(16):
    print(k,n,'direct',direct[k],'blocks',[c[k] for c in counts])
