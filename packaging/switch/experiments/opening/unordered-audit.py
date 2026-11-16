"""Only benchmark if emitted guest instruction streams actually differ."""
from pathlib import Path
import subprocess,re,collections
d=Path('build/switch-runtime/core-perf')
tot=collections.Counter()
for u in (2,10,16,26,39):
 rows=[]
 for i,g in enumerate(('opening-page-hot-o3','opening-unordered-branch')):
  obj=d/g/f'recomp_{u:04}.c.o'
  sym=None;functions={}
  for l in subprocess.check_output(['/opt/devkitpro/devkitA64/bin/aarch64-none-elf-objdump','-d',obj],text=True).splitlines():
   m=re.match(r'^[0-9a-f]+ <([^>]+)>:',l)
   if m:sym=m[1];functions[sym]=[];continue
   m=re.match(r'^\s*[0-9a-f]+:\s+([0-9a-f]{8})\s+(\S+)',l)
   if m and sym and sym.startswith(('ngb_reg_sub_','ngb_reg_d3d_orig_')):
    functions[sym].append(m[1]);tot['fcmp'+str(i)]+=m[2] in ('fcmp','fcmpe','fccmp','fccmpe')
  rows.append(functions)
 changed=sum(rows[0].get(k)!=v for k,v in rows[1].items() if k.startswith(('ngb_reg_sub_','ngb_reg_d3d_orig_')))
 print('unit',u,'changed guest functions',changed);tot['changed']+=changed
print(tot)
raise SystemExit(0 if tot['changed'] else 3)
