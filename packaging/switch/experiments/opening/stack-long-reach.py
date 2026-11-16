"""Historical entry coverage of long-stack runs, not dynamic block execution counts."""
from pathlib import Path
from collections import Counter
import re,runpy
base=Path('build/switch-runtime')
pat=runpy.run_path(str(Path(__file__).with_name('stack-long-run.py')))['pat']
cnt=Counter()
frames=set()
for f,row in re.findall(r'^\[ENTRY_MIX\] (\d+) (.*)$',(base/'core-perf/opening-setup/entry-mix.log').read_text(),re.M):
    if 31<=int(f)<=120:
        assert f not in frames
        frames.add(f)
        for a,n in re.findall(r'([0-9a-f]+):(\d+)',row):cnt[int(a,16)]+=int(n)
assert len(frames)==90
totals=Counter();rank=[];owners={}
for src in sorted((base/'gen').glob('recomp_[0-9][0-9][0-9][0-9].c')):
    u=int(src.stem.split('_')[1])
    source=re.sub(r'#ifdef NGB_DIRECT3D\n(void d3d_orig_\w+\(void\))\n#else\nvoid sub_\w+\(void\)\n#endif',r'\1',src.read_text())
    for m in re.finditer(r'^void (?:sub_|d3d_orig_)([0-9A-F]+)\(void\)\n\{(.*?)^\}',source,re.M|re.S):
        if not pat.search(m[2]):continue
        n=cnt[int(m[1],16)]
        owners[m[1].upper()]=u
        totals[u]+=n
        if n:rank.append((n,m[1],u))
print("entry visits/frame (not group executions) in trial units / all:",sum(totals[i] for i in (1,9,15))/90,sum(totals.values())/90)
print("highest recorded owners", sorted(rank,reverse=True)[:10])

# Direct guest PC only, using this device build's own symbol archive.
import json
archive=base/'history/0.51.0-rc1'
api=runpy.run_path('packaging/switch/analyze-profile.py')
sym=api['load_symbols'](archive/'symbols.gz')
hardware=base/json.loads((archive/'deployment.json').read_text())['hardware_log']
rows=api['parse_windows'](hardware.read_text().splitlines())[1,120]['profiles']['guest'][1]
hits=Counter()
for frame,_,_,_,_,pcs in rows:
    if not 31<=frame<=120 or not pcs:continue
    hits['delivered']+=1
    m=re.fullmatch(r'(?:ngb_reg_)?(?:sub_|d3d_orig_)([0-9A-Fa-f]+)(?:\..*)?',sym(pcs[0]))
    if m:
        hits['named guest']+=1
        u=owners.get(m[1].upper())
        if u is not None:hits['any owner']+=1
        if u in (1,9,15):hits['trial owner']+=1
print("older device exclusive PC in containing functions, not inside stack runs:",dict(hits))
