"""Collapse only service-free runs clearing the eight static light records."""
from pathlib import Path
def transform(s):
    label='loc_00308170: ;'
    assert s.count(label)==1
    code = """
    {
        /* 124-byte records. Division and modulo have a constant divisor;
           reject unexpected guest addresses before touching any state. */
        uint32_t off = edi - 0x9AC118u;
        if (off < 8u*124u && off % 124u == 0 && ngb_fast_ram) {
            uint32_t count = 8u - off / 124u, mask = ngb_poll_mask;
            if (mask && !(mask & (mask+1u)) && !ngb_pending_dpcs &&
                count <= mask - ((uint32_t)ngb_guest_polls & mask)) {
                ngb_guest_polls += count;
                for (; edi < 0x9AC4F8u; edi += 124u)
                    *(volatile uint32_t *)(ngb_fast_ram + edi) = 0;
                _fa = edi; _fas = (int32_t)edi;
                _fb = 0x9AC4F8u; _fbs = (int32_t)_fb;
                goto loc_00308181;
            }
        }
    }
    """
    return s.replace(label,label+code)
if __name__=='__main__':
    p=Path(__file__).parent
    src=(p/'page-hot-o3.py').read_text()
    a=src.index('next_set=');b=src.index('parent=d.parent',a)
    src=src[:a]+"d=(base/'core-perf/opening-light-clear').resolve();d.mkdir(exist_ok=True)\n"+src[b:]
    a=src.index('names=');b=src.index('\ns=s[:s.index',a)
    src=src[:a]+"""names=['recomp_0028.c']
(d/names[0]).write_text(transform((base/'gen'/names[0]).read_text()))
"""+src[b:]
    a=src.index('s=s.replace(k," c[-1:');b=src.index('\nexec(compile',a)
    src=src[:a]+'''s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)'''+src[b:]
    exec(compile(src,'tree-level-build','exec'),{'transform':transform})
    Path('build/switch-runtime/core-perf/opening-light-clear/recomp_0028.c').unlink()
