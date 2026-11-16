"""Compile the exact transformed tail groups beside reference groups; compare register file, RAM, fallback order."""
from pathlib import Path
from collections import Counter
import runpy,tempfile,subprocess
p=Path(__file__).parent;b=runpy.run_path(str(p/'shared-pop-tail.py'));groups=set()
for u in b['units']:
 s=Path(f'build/switch-runtime/gen/recomp_{u:04}.c').read_text()
 counts=Counter(m[0] for m in b['pat'].finditer(s));groups.update(x for x,n in counts.items() if n>=8)
groups=sorted(groups)
mock=(p/'stack-groups-check.inc').read_text().replace('#define ebp st.r[5]','').replace('i*127491+6835','4096+4*(i%1024)').replace('initial.r[4]=8192+side*4;', 'initial.r[5]=8192-side*4;initial.r[4]=8192+side*4;')
def gen(tag):
 return ''.join(f'void {tag}{i}_{j}(void)\n{{\n    uint32_t ebp = 0;\n    ebp = st.r[5];\n'+raw+'\n}\n' for i,raw in enumerate(groups) for j in range(8))
k='#include "recomp_funcs.h"'
s=mock+gen('ref')+b['transform'](k+'\n'+gen('opt'),0).replace(k,'').replace(',noclone','')
for name,tag in [('reference','ref'),('candidate','opt')]:
 s+=f'static void {name}(unsigned i){{switch(i){{'+''.join(f'case {i}:{tag}{i}_0();break;' for i in range(len(groups)))+'default:abort();}}\n'
s+=f'int main(void){{return check({len(groups)});}}'
with tempfile.TemporaryDirectory() as t:
 f=Path(t)/'tails.c';f.write_text(s);exe=f.with_suffix('');subprocess.run(['cc','-O2',f,'-o',exe],check=True);subprocess.run([exe],check=True)
