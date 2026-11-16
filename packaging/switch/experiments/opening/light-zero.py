"""Coalesce the 26 zero stores for the ordinary forward XDK light initializer."""
from pathlib import Path
def transform(s):
    a=s.index('loc_003C7879: ;');b=s.index('loc_003C78B9: ;',a)
    old='{ uint32_t _i; int32_t _st = RECOMP_DF_STEP(4); for (_i = 0; _i < ecx; _i++) MEM32(edi + _i*_st) = eax; edi += ecx * _st; }'
    assert s[a:b].count(old)==1
    new="""if (ecx==26 && !eax && RECOMP_DF_STEP(4)==4 &&
            (edi & 4095u)+104u <= ngb_fast_page_bytes[edi >> 12]) {
        __builtin_memset(ngb_fast_ram + (edi & 0x7fffffffu), 0, 104);
        edi += 104;
    } else """+old
    return s[:a]+s[a:b].replace(old,new)+s[b:]
if __name__=='__main__':
    p=Path(__file__).parent
    src=(p/'page-hot-o3.py').read_text()
    a=src.index('next_set=');b=src.index('parent=d.parent',a)
    src=src[:a]+"d=(base/'core-perf/opening-light-zero').resolve();d.mkdir(exist_ok=True)\n"+src[b:]
    a=src.index('names=');b=src.index('\ns=s[:s.index',a)
    src=src[:a]+"""names=['recomp_0044.c']
(d/names[0]).write_text(transform((base/'gen'/names[0]).read_text()))
"""+src[b:]
    a=src.index('s=s.replace(k," c[-1:');b=src.index('\nexec(compile',a)
    src=src[:a]+'''s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)'''+src[b:]
    exec(compile(src,'tree-level-build','exec'),{'transform':transform})
    Path('build/switch-runtime/core-perf/opening-light-zero/recomp_0044.c').unlink()
