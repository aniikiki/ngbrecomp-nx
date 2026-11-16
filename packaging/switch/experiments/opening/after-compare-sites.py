"""Resolve sampled libc equality callers using the retained ELF map and exact object relocations."""
from pathlib import Path
import re, subprocess, bisect
from collections import Counter, defaultdict
d = Path('build/switch-runtime/core-perf/opening-after-profile')
symbols = {}
for line in (d/'symbols.txt').read_text().splitlines():
    a,n,_,name = line.split(maxsplit=3)
    a,n = int(a,16),int(n,16)
    if n > symbols.get(a,(0,''))[0]: symbols[a] = n,name
keys = sorted(symbols)
sites = defaultdict(list)
for obj in sorted((d/'host').glob('*.o')):
    asm = subprocess.check_output(['objdump','-dr',obj],text=True)
    for ln in asm.splitlines():
        m = re.match(r'^([\da-f]+) <([^>]+)>:',ln)
        if m: base,name = int(m[1],16),m[2]
        m = re.match(r'^\s*([\da-f]+): R_AARCH64_(?:CALL|JUMP)26\s+(\S+)',ln)
        if m: sites[name,int(m[1],16)-base].append((obj.name,m[2]))
counts = defaultdict(Counter)
for i in range(1,5):
    s = (d/f'run-{i}.log').read_text()
    assert 'verified 120 original demo frames' in s
    pcs = {(f,p) for f,p in re.findall(r'^\[FRAME_MODULE\] (\d+) (\w+) \w+ \S+/libc.so.6 __memcmpeq$',s,re.M)}
    for f,p,lr in re.findall(r'^\[FRAME_LR\] (\d+) (\w+) (\w+)$',s,re.M):
        if int(f)<=30 or (f,p) not in pcs: continue
        addr = int(lr,16)-4
        idx = bisect.bisect_right(keys,addr)-1
        key = 'unresolved'
        if idx>=0:
            a = keys[idx]; n,name = symbols[a]; off = addr-a
            if off<n: key = f'{name}+{off:x} {sites.get((name,off),[])}'
        counts[key][i]+=1
for k,c in sorted(counts.items(), key=lambda pair:-sum(pair[1].values())):
    print(sum(c.values()),[c[i] for i in range(1,5)],k)
