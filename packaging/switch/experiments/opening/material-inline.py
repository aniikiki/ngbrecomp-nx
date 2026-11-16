"""Inline the unmodified material interpreter at its three direct model-submit sites."""
from pathlib import Path
def transform(s):
    parent='sub_0030BCA0';callee='sub_0030C240'
    sig='void '+callee+'(void)'
    a=s.index(sig+'\n{');b=s.index('\n}',a)+2
    body=s[a:b].replace(sig,'static inline __attribute__((always_inline)) void material_inline(void)',1)
    a=s.index('void '+parent+'(void)\n{');b=s.index('\n}',a)+2
    original=s[a:b];k='RECOMP_ABI_CALL(0x0030C240u, sub_0030C240)'
    assert original.count(k)==3
    return s[:a]+body+'\n'+original.replace(k,k.replace(callee,'material_inline'))+s[b:]
if __name__=='__main__':
    p=Path(__file__).parent
    src=(p/'page-hot-o3.py').read_text()
    a=src.index('next_set=');b=src.index('parent=d.parent',a)
    src=src[:a]+"d=(base/'core-perf/opening-material-inline').resolve();d.mkdir(exist_ok=True)\n"+src[b:]
    a=src.index('names=');b=src.index('\ns=s[:s.index',a)
    src=src[:a]+"""names=['recomp_0028.c']
(d/names[0]).write_text(transform((base/'gen'/names[0]).read_text()))
"""+src[b:]
    a=src.index('s=s.replace(k," c[-1:');b=src.index('\nexec(compile',a)
    src=src[:a]+'''s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)'''+src[b:]
    exec(compile(src,'tree-level-build','exec'),{'transform':transform})
    Path('build/switch-runtime/core-perf/opening-material-inline/recomp_0028.c').unlink()
