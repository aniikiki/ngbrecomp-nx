"""Rank unswitched units from three independently symbolized 31..120 PC samples."""
from pathlib import Path
from bisect import bisect_right
from collections import Counter
import re
base=Path('build/switch-runtime');d=base/'core-perf/opening-frame-pc'
units={}
for p in (base/'gen').glob('recomp_[0-9][0-9][0-9][0-9].c'):
    for fn in re.findall(r'^void (sub_[0-9A-F]+)\(void\)$',p.read_text(),re.M):
        units[fn]=int(p.stem[-4:])
counts=[]
for tag,syms in [('initial','initial'),('modules','module'),('lr','lr')]:
    s=(d/f'distribution-{tag}.log').read_text()
    assert 'verified 120 original demo frames' in s
    byaddr={}
    for l in (d/f'{syms}-symbols.txt').read_text().splitlines():
        a,n,_,name=l.split(maxsplit=3);a=int(a,16);n=int(n,16)
        if n>byaddr.get(a,(0,''))[0]:byaddr[a]=(n,name)
    keys=sorted(byaddr);c=Counter()
    for f,pc in re.findall(r'^\[FRAME_PC\] (\d+) ([0-9a-f]+)$',s,re.M):
        if not 31<=int(f)<=120:continue
        pc=int(pc,16);j=bisect_right(keys,pc)-1
        if j<0:continue
        a=keys[j];n,name=byaddr[a];u=units.get(name.removeprefix('ngb_reg_'))
        if pc<a+n and u is not None:c[u]+=1
    counts.append(c)
for u in sorted(set.union(*(set(c) for c in counts))-{2,10,16,26,39},key=lambda u:(-sum(c[u] for c in counts),u))[:10]:
    print(u,*[c[u] for c in counts])
