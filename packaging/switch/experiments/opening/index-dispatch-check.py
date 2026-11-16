"""Compile actual rewritten branches separately and compare against original
branches for every original index with every possible local destination, plus
invalid destinations, wrapped indices and fallback. No game files are copied."""
import runpy,tempfile,subprocess
from pathlib import Path
d=runpy.run_path(str(Path(__file__).with_name('index-dispatch.py')))
import re
parts=['#include <stdint.h>\n#include <stdlib.h>\nstatic uint32_t addr,reads,value;\n#define MEM32(a) (reads++,addr=(a),value)\n']
calls=[]
for unit in (0,2):
    s=(d['base']/'gen'/f'recomp_{unit:04}.c').read_text()
    for m in d['site'].finditer(s):
        cand,stats=d['transform'](m[0])
        if not stats:continue
        _,reg,base,n,_,arms=m.groups()
        k=len(calls)
        entries=re.findall(r'goto loc_([0-9A-F]+);',arms)
        for j,body in enumerate((m[0],cand)):
            parts.append(f'static uint32_t f{k}_{j}(uint32_t {reg}) {{\n'+body+'return 0; }\n'+''.join(f'loc_{v}:return 0x{v};\n' for v in entries)+'}\n')
        parts.append(f'static void t{k}(void) {{uint32_t targets[]={{0,1,~0u,'+','.join('0x'+v for v in entries)+'};\n'+
            f'for(uint32_t i=0;i<{n}+4;i++) for(unsigned j=0;j<sizeof(targets)/4;j++) {{uint32_t idx=i<{n}+2?i:0u-i; value=targets[j]; reads=0; uint32_t a=f{k}_0(idx),b=f{k}_1(idx); if(a!=b||reads!=2||addr!=idx*4+{base}u) abort();}}}}\n')
        calls.append(f't{k}();')
parts.append('int main(void){'+''.join(calls)+'}\n')
with tempfile.TemporaryDirectory() as temp:
    c=Path(temp)/'check.c';exe=c.with_suffix('')
    c.write_text(''.join(parts));subprocess.run(['cc','-O2',str(c),'-o',str(exe)],check=True);subprocess.run([str(exe)],check=True)
print(len(calls),'rewritten dispatch sites passed')
