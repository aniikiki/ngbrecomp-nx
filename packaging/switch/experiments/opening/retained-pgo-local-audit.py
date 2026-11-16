"""Check the private guest entry surface and whether local binding changed actual call sites."""
from pathlib import Path
from collections import Counter
import re,subprocess
root=Path('/work/build/switch-runtime/core-perf')
prefix='/opt/devkitpro/devkitA64/bin/aarch64-none-elf-'
changed=0
for u in (2,10,16,28,29):
    def inspect(folder):
        obj=root/folder/f'recomp_{u:04}.c.o'
        syms=subprocess.check_output([prefix+'nm','--defined-only','-g',obj],text=True)
        exported={line.split()[-1] for line in syms.splitlines()}
        asm=subprocess.check_output([prefix+'objdump','-d','--no-show-raw-insn',obj],text=True)
        op=Counter(re.findall(r'^\s*[\da-f]+:\s+([a-z][a-z0-9.]*)\b',asm,re.M))
        return exported,(sum(op.values()),op['bl'],op['blr'])
    old,a=inspect('opening-retained-pgo')
    new,b=inspect('opening-retained-pgo-local')
    assert old==new and any(s.startswith('ngb_reg_sub_') for s in old),(u,old^new)
    print(u,len(old),a,b,'delta',tuple(y-x for x,y in zip(a,b)),flush=True)
    changed+=abs(b[1]-a[1])
assert changed,'no measured change in direct call instruction count'
