"""Symbolize frame-pointer chains against the exact Linux replay executable."""
from bisect import bisect_right
from collections import Counter
import re
import subprocess
import sys
from pathlib import Path

elf, log = sys.argv[1:3]
nm = subprocess.check_output(['nm','-n','-S',elf], text=True)
base = int(next(l.split()[0] for l in nm.splitlines() if l.endswith(' __executable_start')),16)
symbols = sorted((int(a,16),int(b,16),name) for a,b,name in
                 re.findall(r'^([0-9a-f]+) ([0-9a-f]+) [tTWw] (.+)$',nm,re.M) if int(b,16))
# Earlier package gates have .type but no .size. Their short assembly
# bodies extend to the next text symbol (never across unrelated sections).
texts=sorted(set(int(a,16) for a in re.findall(r'^([0-9a-f]+) (?:[0-9a-f]+ )?[tTwW] ',nm,re.M)))
for a, name in re.findall(r'^([0-9a-f]+) [Tt] (ngb_gate_\w+)$',nm,re.M):
    address=int(a,16); ix=bisect_right(texts,address)
    if ix<len(texts) and texts[ix]-address<=256:symbols.append((address,texts[ix]-address,name))
symbols.sort()
starts = [s[0] for s in symbols]
def function(offset):
    addr = base+int(offset,16)
    i = bisect_right(starts,addr)-1
    if i<0 or addr>=starts[i]+symbols[i][1]:return '(external/unknown)'
    return symbols[i][2].removeprefix('ngb_reg_').removesuffix('.localalias')
chains = [[function(pc) for pc in line.split()[1:]] for line in Path(log).read_text().splitlines()
          if line.startswith('[ARMCHAIN] ')]
if not chains:sys.exit('no native chains')
print(f'{len(chains)} samples; {sum(len(s)>3 for s in chains)} with >=4 frames')
roots = sys.argv[3:] or ['sub_001CB510','sub_001CC5A0','sub_000298F0','sub_00147DF0']
for root in roots:
    hits=Counter()
    for stack in chains:
        if root not in stack:continue
        j=stack.index(root)
        # Exclude duplicate names from the public and private entry wrappers.
        path=[]
        for s in reversed(stack[:j]):
            if s!=root and (not path or s!=path[-1]):path.append(s)
        hits[tuple(path[:6])]+=1
    print(root, sum(hits.values()),'inclusive samples; child paths:')
    for path,count in hits.most_common(6):print(f'  {count:4}', ' > '.join(path) or '(self)')
