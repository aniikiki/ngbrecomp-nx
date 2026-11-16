"""Compile real original/candidate dispatch arms. Exercise original targets,
overlapping low-bit buckets, and arbitrary loaded 32-bit guest destinations."""
import re,runpy,subprocess,tempfile
from pathlib import Path
import sys
p=Path(__file__).with_name('target-switch.py' if '--target-switch' in sys.argv else 'jump-buckets.py')
a=runpy.run_path(str(p))
src=['#include <stdint.h>']
calls=[]
for unit in (0,2):
    s=Path(f'build/switch-runtime/gen/recomp_{unit:04}.c').read_text()
    for m in a['pat'].finditer(s):
        if int(m[2])<16:continue
        i=len(calls)
        val=re.findall(r'if \(_jt == (0x[0-9A-F]+u)\)',m['arms'])
        for name,arms in [('old',m[0]),('new',a['transform'](m[0]))]:
            body=arms.split('\n',1)[1]
            src.append(f'static unsigned {name}{i}(uint32_t _jt){{\n'+body+
                'return 0;\n'+''.join('loc_'+v[2:-1]+':return '+v+';\n' for v in val)+'}')
        calls.append(f'{{uint32_t v[]={{'+','.join(val)+f'}}; for(unsigned j=0;j<sizeof(v)/sizeof(v[0]);j++){{ uint32_t x=v[j]; if(old{i}(x)!=x || new{i}(x)!=x)return 1; for(unsigned b=0;b<32;b++){{uint32_t y=x^(1u<<b); if(new{i}(y)!=old{i}(y))return 2;}}}} for(unsigned j=0;j<10000;j++){{seed=1664525u*seed+1013904223u;if(new{i}(seed)!=old{i}(seed))return 3;}}}}')
assert len(calls)==14
src.append('int main(void){uint32_t seed=21;'+''.join(calls)+'return 0;}')
with tempfile.TemporaryDirectory() as d:
    f=Path(d)/'check.c';f.write_text('\n'.join(src))
    subprocess.run(['cc','-std=c11','-O1',str(f),'-o',d+'/check'],check=True)
    subprocess.run([d+'/check'],check=True)
print('14 actual dispatch sites: all listed destinations, every one-bit mutation, and 140000 random destinations matched')
