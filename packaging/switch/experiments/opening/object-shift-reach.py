"""Reach of straight-line in-place scalar arithmetic with one stable address base."""
from pathlib import Path
from collections import Counter
import re,runpy,json
root=Path('build/switch-runtime')
pat=re.compile(r'    (xmm\d+) = XMM_SCALAR\(MEMF\(((e[abcd]x|e[sd]i|ebp|esp)(?: \+ (-?(?:0x[\dA-Fa-f]+|\d+)))?)\)\); /\* movss \*/\n    \1\.f\[0\] = \1\.f\[0\] ([+*/-]) (xmm\d+)\.f\[0\]; /\* [^*]+ \*/\n    MEMF\(\2\) = \1\.f\[0\]; /\* movss \*/\n')
owners=Counter()
for p in (root/'gen').glob('recomp_*.c'):
    for f,b in re.findall(r'void sub_([0-9A-F]+)\(void\)\n\{(.*?)\n\}',p.read_text(),re.S):
        prev=-1;base=None;offsets=[]
        for m in pat.finditer(b):
            if m.start()!=prev or m[3]!=base:
                if len(offsets)>=3 and max(offsets)-min(offsets)<=4092:owners[f]+=len(offsets)
                offsets=[]
            offsets.append(int(m[4] or '0',0));prev=m.end();base=m[3]
        if len(offsets)>=3 and max(offsets)-min(offsets)<=4092:owners[f]+=len(offsets)
print('functions / operations (static):',len(owners),sum(owners.values()))
h=root/'history/0.51.0-rc1';api=runpy.run_path('packaging/switch/analyze-profile.py')
sym=api['load_symbols'](h/'symbols.gz');device=root/json.loads((h/'deployment.json').read_text())['hardware_log']
samples=api['parse_windows'](device.read_text().splitlines())[1,120]['profiles']['guest'][1]
for lo,hi in ((1,30),(31,120)):
    c=Counter();n=0
    for fr,*_,pcs in samples:
        if not lo<=fr<=hi:continue
        n+=1;m=re.search(r'(?:sub|orig)_([0-9A-F]{8})(?:\b|_)',sym(pcs[0]))
        if m and m[1] in owners:c[m[1]]+=1
    print('device leaf in a containing function',lo,hi,sum(c.values()),'/',n,c.most_common())
