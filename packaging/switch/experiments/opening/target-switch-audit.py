"""Report the actual generated branches in each affected function, not an estimated cycle saving."""
import re,shutil,subprocess,runpy
from pathlib import Path
p=Path(__file__).parent
f=runpy.run_path(str(p/'target-switch.py'))
root=Path('build/switch-runtime')
tool=shutil.which('llvm-objdump') or subprocess.check_output(['xcrun','-f','llvm-objdump'],text=True).strip()
for unit,group in ((0,'opening-full-page'),(2,'opening-compact-loops')):
    src=(root/'gen'/f'recomp_{unit:04}.c').read_text()
    for m in re.finditer(r'^void (\w+)\(void\)\n\{(.*?)^\}',src,re.M|re.S):
        num=sum(int(x[2])>=16 for x in f['pat'].finditer(m[2]))
        if not num:continue
        both=[]
        for g in (group,'opening-target-switch'):
            obj=root/'core-perf'/g/f'recomp_{unit:04}.c.o'
            text=subprocess.check_output([tool,'--disassemble-symbols=ngb_reg_'+m[1],str(obj)],text=True)
            ops=re.findall(r'^\s*[0-9a-f]+:\s+[0-9a-f]{8}\s+(\S+)',text,re.M)
            assert ops,m[1]
            both.append((len(ops),sum(x in ('b.eq','b.ne') for x in ops),sum(x.startswith('b.') and x not in ('b.eq','b.ne') for x in ops),ops.count('br')))
        print(m[1],num,'sites; (instructions, equality branches, other conditional branches, indirect branches)',*both)
