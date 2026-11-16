"""Check that code actually changed. Do not benchmark an identical build."""
from pathlib import Path
import subprocess,re,collections
base=Path('build/switch-runtime/core-perf')
tool='/opt/devkitpro/devkitA64/bin/aarch64-none-elf-objdump'
for label in ['opening-full-guest','opening-guest-frame']:
 count=collections.Counter()
 for u in (0,2,27,28,44):
    path=base/label/f'recomp_{u:04}.c.o'
    s=subprocess.check_output([tool,'-d',str(path)],text=True)
    count['sets_fp']+=len(re.findall(r'\bmov\s+x29, sp\b',s))
    count['fp_lr_preindex']+=len(re.findall(r'\bstp\s+x29, x30, \[sp, #-[0-9]+\]!',s))
    count['insns']+=len(re.findall(r'^\s*[0-9a-f]+:\s+[0-9a-f]{8}\s+',s,re.M))
 print(label,dict(count),flush=True)
 if label=='opening-full-guest':before=count
 else:assert count['sets_fp']<before['sets_fp'], 'no frame-pointer reduction'
