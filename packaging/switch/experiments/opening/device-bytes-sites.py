"""Resolve byte-helper samples only where the saved return PC follows BL to that helper."""
from collections import Counter
from pathlib import Path
import json,re,runpy
base=Path('build/switch-runtime')
release=base/'history/0.51.0-rc1'
api=runpy.run_path(str(Path(__file__).resolve().parents[2]/'analyze-profile.py'))
sym=api['load_symbols'](release/'symbols.gz')
dep=json.loads((release/'deployment.json').read_text())
rows=api['parse_windows']((base/dep['hardware_log']).read_text().splitlines())[1,120]['profiles']['guest'][1]
lines=(base/'core-perf/opening-setup/leaf-budget.tsv').read_text().splitlines()
leaf=[x.split('\t') for x in lines if re.match(r'^\d+\t',x)]
rows=[r for r in rows if 1<=r[0]<=120];assert len(rows)==len(leaf)
window=(base/dep['hardware_log']).read_text().split('[PROFILE_WINDOW] first=1 last=120',1)[1].split('[PROFILE_WINDOW]',1)[0]
pairs=[tuple(int(x,16) for x in pair.split('/')) for line in window.splitlines() if line.startswith('[PC] ') for pair in line.split()[1:]]
assert len(pairs)==len(rows)
counts=Counter();den=0
with (release/'ngb-startup.nro').open('rb') as n:
 assert bytes.fromhex(lines[0].split()[3])==n.read(84)[64:84]
 for (f,w,scope,_,_,pcs),rec,(pc,lr) in zip(rows,leaf,pairs):
    assert pc==pcs[0]
    assert (f,w,pcs[0])==(int(rec[0]),int(rec[1]),int(rec[2],16))
    if f<31 or w!=1:continue
    den+=1
    if rec[3] not in ('memcmp','memcpy','memset'):continue
    found=False
    # PC rows retain the live LR even when the leaf has no frame record.
    p=lr-4
    n.seek(p);ins=int.from_bytes(n.read(4),'little')
    if ins>>26==0b100101:
        imm=ins&0x3ffffff
        target=p+4*(imm-(1<<26) if imm&(1<<25) else imm)
        if sym(target)==rec[3]:
            counts[rec[3],sym(p),hex(p)]+=1;found=True
    if not found:counts[rec[3],'unresolved','-']+=1
print('delivered worker 1 frames 31..120',den)
for k,v in counts.most_common():print(v,*k)
