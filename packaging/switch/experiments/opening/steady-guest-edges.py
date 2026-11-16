"""Select guest call edges on one historic device slice; validate on the next.
Visible stacks only. Restrict to guest leaves and exclude visible model submit."""
from pathlib import Path
from collections import Counter
import json,re,runpy
base=Path('build/switch-runtime')
h=base/'history/0.51.0-rc1'
api=runpy.run_path('packaging/switch/analyze-profile.py')
sym=api['load_symbols'](h/'symbols.gz')
log=base/json.loads((h/'deployment.json').read_text())['hardware_log']
w=api['parse_windows'](log.read_text().splitlines())[1,120]
bins=[Counter(),Counter()];n=[0,0];kept=[0,0];leaf=[Counter(),Counter()]
for f,*_,pcs in w['profiles']['guest'][1]:
 if not 61<=f<=120:continue
 b=(f-61)//30;n[b]+=1
 t=[sym(a).replace('ngb_reg_','').split('.')[0] for a in pcs]
 if 'sub_0030BCA0' in t or not re.fullmatch('sub_[0-9A-F]{8}',t[0]):continue
 kept[b]+=1
 # Immediate guest caller only; don't bridge missing/unresolved runtime frames.
 if len(t)>1 and re.fullmatch('sub_[0-9A-F]{8}',t[1]):bins[b][t[1],t[0]]+=1
 leaf[b][t[0]]+=1
print('delivered/selected',n,kept,'direct guest pair',list(map(Counter.total,bins)) if hasattr(Counter,'total') else [sum(c.values()) for c in bins])
for title,items in [('leaf',leaf),('edge',bins)]:
 keys=[k for k,_ in sorted(items[0].items(),key=lambda kv:(-kv[1],kv[0]))[:5]]
 print(title,[(k,items[0][k],items[1][k]) for k in keys], 'selection coverage',sum(items[1][k] for k in keys),'/',kept[1])
