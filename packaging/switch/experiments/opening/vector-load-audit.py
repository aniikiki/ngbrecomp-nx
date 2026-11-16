"""Count adjacent data-linked GP pair -> machine stack -> SIMD reload, including one intervening non-memory instruction."""
from pathlib import Path
import subprocess,re
root=Path('build/switch-runtime/core-perf')
def count(group):
 n=0
 for u in [0,28,29]:
  s=subprocess.check_output(['/opt/devkitpro/devkitA64/bin/aarch64-none-elf-objdump','-d',root/group/f'recomp_{u:04}.c.o'],text=True)
  n+=len(re.findall(r'\bldp\s+(x\d+), (x\d+), \[x\d+[^\]]*\]\s*\n\s*\w+:\s+\w+\s+stp\s+\1, \2, \[(sp(?:, #-?\d+)?)\]\s*\n(?:\s*\w+:\s+\w+\s+(?:add|adrp|mov)\s+[^\n]+\n)?\s*\w+:\s+\w+\s+ldr\s+q\d+, \[\3\]',s))
 return n
a=count('opening-full-page');b=count('opening-vector-load-lane')
print('matched stack transits:',a,'->',b,flush=True)
assert a>0 and b<a,'mechanism did not reduce matched transits'
