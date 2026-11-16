"""Measure the sampled footprint of all eligible comparison owners on independent runs."""
from bisect import bisect_right
from collections import Counter
from contextlib import redirect_stdout
from pathlib import Path
import io,json,re,runpy
p=Path(__file__).parent
with redirect_stdout(io.StringIO()):
    owners=runpy.run_path(str(p/'ordered-branch-rank.py'))['owners']
base=Path('build/switch-runtime')
def owner(sym):
    m=re.fullmatch(r'(?:ngb_reg_)?(?:sub_|d3d_orig_)([0-9a-fA-F]+)(?:\..*)?',sym)
    return int(m[1],16) if m else None
def report(label,rows):
    for lo,hi in ((1,30),(31,120)):
        c=Counter(va for f,va in rows if lo<=f<=hi)
        print(label,lo,hi,'all',sum(c.values()),'all eligible functions',sum(c[k] for k in owners),'30D630',c[0x30d630],'top',[(hex(k),v) for k,v in c.most_common() if k in owners][:4])
for dirname in ('opening-xdk-pc-scope','opening-outside-operand'):
    d=base/'core-perf'/dirname
    tab=sorted((int(a,16),int(n,16),name) for a,n,_,name in (l.split(maxsplit=3) for l in (d/'symbols.txt').read_text().splitlines()))
    starts=[x[0] for x in tab];rows=[]
    for i in range(1,5):
        s=(d/f'run-{i}.log').read_text();assert 'verified 120 original demo frames' in s
        local={(int(f),int(pc,16)) for f,pc,path in re.findall(r'^\[FRAME_MODULE\] (\d+) (\w+) \w+ (\S+) \S+$',s,re.M) if Path(path).name=='replay'}
        for f,pc in re.findall(r'^\[D3D_SCOPE_PC\] (\d+) \d+ (\w+)$',s,re.M):
            f=int(f);pc=int(pc,16);j=bisect_right(starts,pc)-1
            va=owner(tab[j][2]) if (f,pc) in local and j>=0 and pc<starts[j]+tab[j][1] else None
            rows.append((f,va))
    report(dirname,rows)
h=base/'history/0.51.0-rc1'
api=runpy.run_path('packaging/switch/analyze-profile.py')
sym=api['load_symbols'](h/'symbols.gz');log=base/json.loads((h/'deployment.json').read_text())['hardware_log']
win=api['parse_windows'](log.read_text().splitlines())[1,120]
report('Switch historical rc1',[(f,owner(sym(pcs[0]))) for f,_,_,_,_,pcs in win['profiles']['guest'][1]])
