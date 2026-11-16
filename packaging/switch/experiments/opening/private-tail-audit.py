"""Check final objects: every removed guest CALL26 has a matching JUMP26."""
from pathlib import Path
from collections import Counter
import subprocess,re
d=Path('build/switch-runtime/core-perf')
readelf='/opt/devkitpro/devkitA64/bin/aarch64-none-elf-readelf'
def edges(f):
 text=subprocess.check_output([readelf,'-rW',f],text=True)
 return Counter((kind,sym) for kind,sym in re.findall(r'R_AARCH64_(CALL26|JUMP26)\s+[0-9a-fA-F]+\s+(\S+)',text))
for u in [2,10,16,26,39]:
 obj=f'recomp_{u:04}.c.o'
 a,b=[edges(d/k/obj) for k in ['opening-page-hot-o3','opening-private-tail']]
 total=0
 for sym in set(s for _,s in a|b):
  removed=a['CALL26',sym]-b['CALL26',sym]
  assert removed==b['JUMP26',sym]-a['JUMP26',sym] and removed>=0,(u,sym)
  assert not removed or sym.startswith('ngb_reg_sub_')
  total+=removed
 print(u,'cross-section calls changed to branches:',total)
