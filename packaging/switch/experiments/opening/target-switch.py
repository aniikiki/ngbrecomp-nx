"""Branch on the full loaded guest VA. A sparse C switch lets GCC balance the target comparisons."""
import re,runpy
from pathlib import Path
p=Path(__file__).parent
pat=runpy.run_path(str(p/'jump-buckets.py'))['pat']
def transform(s,unit=None):
    def replace(m):
        if int(m[2])<16:return m[0]
        pairs=re.findall(r'if \(_jt == 0x([0-9A-F]+)u\) goto loc_([0-9A-F]+);',m['arms'])
        assert len({a for a,b in pairs})==len(pairs)==int(m[2]) and all(a==b for a,b in pairs)
        return m['header']+'    switch (_jt) {\n'+''.join(f'    case 0x{a}u: goto loc_{b};\n' for a,b in pairs)+'    default: break;\n    }\n'
    return pat.sub(replace,s)
if __name__=='__main__':
    runpy.run_path(str(p/'model-copy.py'))['build']('target-switch',[(True,[2]),(False,[0])],transform)
