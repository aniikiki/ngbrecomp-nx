from pathlib import Path
import re,collections
d=Path('build/switch-runtime/core-perf/opening-rng-correspondence')
s=(d/'dma-mix.log').read_text()
assert 'reason=verified 120 original demo frames' in s
regs=Path('xboxrecomp/src/nv2a/nv2a_regs.h').read_text()
names=collections.defaultdict(list)
for n,v in re.findall(r'^#\s*define (NV097_\w+)\s+(0x[\da-fA-F]+)\s*$',regs,re.M):names[int(v,16)].append(n)
rows=[(int(t),int(m,16),int(p),int(n)) for t,m,p,n in re.findall(r'^\[DMA_FALLBACK\] (\d+) ([a-f\d]+) (\d+) (\d+)$',s,re.M)]
other,qualified=map(int,re.search(r'^\[DMA_MISC\] (\d+) (\d+)$',s,re.M).groups())
assert rows
print('non-classified Kelvin packets',sum(x[2] for x in rows),'other headers',other,'already eligible but rejected downstream',qualified)
for t,m,p,n in sorted(rows,key=lambda x:-x[2])[:15]:
 print('noninc' if t else 'inc',hex(m),p,n,next(iter(sorted(names[m],key=len)),'?'))
