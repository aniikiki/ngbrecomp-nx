"""Measure actual loaded destinations in the fourteen jump tables. Preserve guest target loads."""
from pathlib import Path
import re,runpy
p=Path(__file__).parent
pat=runpy.run_path(str(p/'jump-buckets.py'))['pat']
def transform(s,u):
    def replace(m):
        if int(m[2])<16:return m[0]
        table=re.search(r'\+ (0x[0-9A-F]+)\); /\* switch:',m['header'])
        assert table,m['header']
        return m['header']+f'    th_observe({table[1]}u,_jt);\n'+m['arms']
    return 'extern void th_observe(unsigned,unsigned);\n'+pat.sub(replace,s)
if __name__=='__main__':
    runpy.run_path(str(p/'model-copy.py'))['build']('target-hist',[(True,[2]),(False,[0])],transform)
