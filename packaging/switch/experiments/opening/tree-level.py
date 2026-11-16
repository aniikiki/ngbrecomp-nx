"""Inline one level of 308D50's actual recursive body, no guessed child or callback."""
from pathlib import Path
def transform(s):
    fn='sub_00308D50'
    a=s.index('void '+fn+'(void)\n{');b=s.index('\n}',a)+2
    body=s[a:b];signature='void '+fn+'(void)'
    key='RECOMP_ABI_CALL(0x00308D50u, sub_00308D50)'
    assert body.count(key)==1
    copy=body.replace(signature,'static inline __attribute__((always_inline)) void tree_one_level(void)',1)
    # The clone descends via the original public function; no recursive
    # always_inline cycle. Preserve the ABI_CHECK wrapper at both sites.
    return s[:a]+copy+'\n'+body.replace(key,key.replace(fn,'tree_one_level'))+s[b:]
if __name__=='__main__':
    p=Path(__file__).parent
    src=(p/'page-hot-o3.py').read_text()
    a=src.index('next_set=');b=src.index('parent=d.parent',a)
    src=src[:a]+"d=(base/'core-perf/opening-tree-level').resolve();d.mkdir(exist_ok=True)\n"+src[b:]
    a=src.index('names=');b=src.index('\ns=s[:s.index',a)
    src=src[:a]+"""names=['recomp_0028.c']
(d/names[0]).write_text(transform((base/'gen'/names[0]).read_text()))
"""+src[b:]
    a=src.index('s=s.replace(k," c[-1:');b=src.index('\nexec(compile',a)
    src=src[:a]+'''s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)'''+src[b:]
    exec(compile(src,'tree-level-build','exec'),{'transform':transform})
    Path('build/switch-runtime/core-perf/opening-tree-level/recomp_0028.c').unlink()
