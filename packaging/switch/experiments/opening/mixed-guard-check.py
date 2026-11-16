"""Check admitted ranges against the ordinary full-page pointer policy, including address aliases."""
import re,runpy
from pathlib import Path
d=Path(__file__).parent;fn=runpy.run_path(str(d/'mixed-fast.py'))['transform']
shapes=set()
for u in (2,10,16,26):
 s=fn(Path(f'build/switch-runtime/gen/recomp_{u:04}.c').read_text())
 for w,body in re.findall(r'\(ms_va&4095u\)\+(\d+)u<=.*?unsigned char \*ms_p=[^;]*;\n(.*?)    }else\{',s,re.S):
  ops=re.findall(r'volatile (\w+) \*\)\(ms_p\+(\d+)\)',body)
  assert len(ops)>=4
  shapes.add((int(w),tuple((int(o),4 if t=='float' else int(re.search(r'\d+',t)[0])//8) for t,o in ops)))
for width,ops in shapes:
 assert min(o for o,n in ops)==0 and max(o+n for o,n in ops)==width
 for base in (0x8000,0x80008000,0xfffff000):
  for off in (0,1,4096-width,4097-width,4095):
   for length in (0,32,4096):
    va=base+off
    if off+width<=length:
     for o,n in ops:
      addr=(va+o)&0xffffffff
      assert addr>>12==va>>12 and (addr&4095)+n<=length and (addr&0x7fffffff)==(va&0x7fffffff)+o
print('distinct actual ordered offset/width patterns:',len(shapes))
