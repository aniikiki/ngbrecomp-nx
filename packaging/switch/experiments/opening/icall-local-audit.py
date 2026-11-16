"""Audit address relocation pairs, including the bad case where GCC ignores a visibility redeclaration."""
from collections import Counter
from pathlib import Path
import re,shutil,subprocess
p=Path('build/switch-runtime/core-perf')
tool=shutil.which('aarch64-none-elf-objdump') or shutil.which('llvm-objdump') or subprocess.check_output(['xcrun','-f','llvm-objdump'],text=True).strip()
symbols={'g_icall_trace','g_icall_trace_idx','g_icall_count','g_xbox_code_hi','g_xbox_code_lo'}
def stats(d,u):
    s=subprocess.check_output([tool,'-r',str(p/d/f'recomp_{u:04}.c.o')],text=True)
    hits=Counter()
    for kind,symbol in re.findall(r'\b(R_AARCH64_\w+)\s+(\w+)',s):
        if symbol in symbols:hits[kind]+=1
    return hits
before=Counter();after=Counter()
for u in (2,10,16,26,39,28):
    before+=stats('opening-compact-loops' if u!=28 else 'opening-full-page',u)
    after+=stats('opening-icall-local',u)
print('baseline',dict(before),'candidate',dict(after))
assert before['R_AARCH64_ADR_GOT_PAGE'] and after['R_AARCH64_ADR_PREL_PG_HI21']
assert not any(n for k,n in after.items() if 'GOT' in k)
