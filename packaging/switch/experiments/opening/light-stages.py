"""Measure both stages of the light updater on the retained widescreen guest."""
from pathlib import Path
def transform(s):
    start=s.index('void sub_00308130(void)\n{')
    end=s.index('\n}',start)+2
    body=s[start:end]
    for i,k in enumerate(('RECOMP_ABI_CALL(0x00317DC0u, sub_00317DC0);','sub_00317D10(); return;')):
        assert body.count(k)==1
        call=k.split(' return;')[0]
        body=body.replace(k,'{ unsigned long long stamp=light_begin('+str(i)+'); '+call+' light_end('+str(i)+',stamp); }'+(' return;' if i else ''))
    return 'extern unsigned long long light_begin(unsigned);extern void light_end(unsigned,unsigned long long);\n'+s[:start]+body+s[end:]
if __name__=='__main__':
    p=Path(__file__).parent
    src=(p/'page-hot-o3.py').read_text()
    a=src.index('next_set=');b=src.index('parent=d.parent',a)
    src=src[:a]+"d=(base/'core-perf/opening-light-stages').resolve();d.mkdir(exist_ok=True)\n"+src[b:]
    a=src.index('names=');b=src.index('\ns=s[:s.index',a)
    src=src[:a]+"""names=['recomp_0028.c']
(d/names[0]).write_text(transform((base/'gen'/names[0]).read_text()))
"""+src[b:]
    a=src.index('s=s.replace(k," c[-1:');b=src.index('\nexec(compile',a)
    src=src[:a]+'''s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)'''+src[b:]
    exec(compile(src,'tree-level-build','exec'),{'transform':transform})
    Path('build/switch-runtime/core-perf/opening-light-stages/recomp_0028.c').unlink()
