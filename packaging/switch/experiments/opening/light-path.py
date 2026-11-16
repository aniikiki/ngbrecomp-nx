"""Count actual REP STOSD execution, eligible bytes and fallback in XDK unit 44."""
from pathlib import Path
import re
def transform(s):
    labels=(0x3c7850,0x3c7879,0x3c78c1,0x3c78e8,0x3c78f1,0x3c794c,0x3c7994,0x3c7996)
    for i,va in enumerate(labels):
        k=f'loc_{va:08X}: ;';assert s.count(k)==1
        s=s.replace(k,k+f' if(lp_on)lp_calls[{i}]++;')
    return 'extern unsigned lp_on,lp_calls[8];\n'+s
if __name__=='__main__':
    p=Path(__file__).parent
    src=(p/'page-hot-o3.py').read_text()
    a=src.index('next_set=');b=src.index('parent=d.parent',a)
    src=src[:a]+"d=(base/'core-perf/opening-light-path').resolve();d.mkdir(exist_ok=True)\n"+src[b:]
    a=src.index('names=');b=src.index('\ns=s[:s.index',a)
    src=src[:a]+"""names=['recomp_0044.c']
(d/names[0]).write_text(transform((base/'gen'/names[0]).read_text()))
"""+src[b:]
    a=src.index('s=s.replace(k," c[-1:');b=src.index('\nexec(compile',a)
    src=src[:a]+'''s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)'''+src[b:]
    exec(compile(src,'tree-level-build','exec'),{'transform':transform})
    Path('build/switch-runtime/core-perf/opening-light-path/recomp_0044.c').unlink()
