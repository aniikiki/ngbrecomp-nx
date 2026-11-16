"""Combine the one or two service-free tickets immediately before descending."""
from pathlib import Path
def transform(s):
    inc='#include "tree_insert.inc"'
    assert s.count(inc)==1
    t=Path('packaging/switch/runtime/tree_insert.inc').read_text()
    k='                        ngb_guest_block_poll();\n                    }\n                    if (!left) ngb_guest_block_poll();'
    assert t.count(k)==1
    return s.replace(inc,t.replace(k, """                    }
                    unsigned n = (jump != 0x00308c8e) + !left;
                    uint64_t ticket = ngb_guest_polls;
                    unsigned mask = ngb_poll_mask;
                    if (!ngb_pending_dpcs && ((ticket+1)&mask) && ((ticket+2)&mask))
                        ngb_guest_polls = ticket+n;
                    else {
                        if (jump != 0x00308c8e) ngb_guest_block_poll();
                        if (!left) ngb_guest_block_poll();
                    }"""))
if __name__=='__main__':
    p=Path(__file__).parent
    src=(p/'page-hot-o3.py').read_text()
    a=src.index('next_set=');b=src.index('parent=d.parent',a)
    src=src[:a]+"d=(base/'core-perf/opening-tree-tickets').resolve();d.mkdir(exist_ok=True)\n"+src[b:]
    a=src.index('names=');b=src.index('\ns=s[:s.index',a)
    src=src[:a]+"""names=['recomp_0028.c']
(d/names[0]).write_text(transform((base/'gen'/names[0]).read_text()))
"""+src[b:]
    a=src.index('s=s.replace(k," c[-1:');b=src.index('\nexec(compile',a)
    src=src[:a]+'''s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)'''+src[b:]
    exec(compile(src,'tree-level-build','exec'),{'transform':transform})
    Path('build/switch-runtime/core-perf/opening-tree-tickets/recomp_0028.c').unlink()
