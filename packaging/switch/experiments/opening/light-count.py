"""Count actual REP STOSD execution, eligible bytes and fallback in XDK unit 44."""
from pathlib import Path
import re
def transform(s):
    old='{ uint32_t _i; int32_t _st = RECOMP_DF_STEP(4); for (_i = 0; _i < ecx; _i++) MEM32(edi + _i*_st) = eax; edi += ecx * _st; }'
    assert s.count(old)==8
    def replace(m):
        va=list(re.finditer(r'loc_([0-9A-F]+):',s[:m.start()]))[-1][1]
        return ("if(lc_on){unsigned i="+str(replace.i)+";lc_va[i]=0x"+va+";lc_calls[i]++;"
                "lc_words[i]+=ecx;if (!eax && RECOMP_DF_STEP(4)==4 && ecx<=1024 && "
                "(edi&4095u)+4u*ecx<=ngb_fast_page_bytes[edi>>12])lc_fast[i]++;}\n"+old)
    replace.i=0
    def step(m):
        t=replace(m);replace.i+=1;return t
    return 'extern unsigned lc_on,lc_va[8],lc_calls[8],lc_fast[8];extern unsigned long long lc_words[8];\n'+re.sub(re.escape(old),step,s)
if __name__=='__main__':
    p=Path(__file__).parent
    src=(p/'page-hot-o3.py').read_text()
    a=src.index('next_set=');b=src.index('parent=d.parent',a)
    src=src[:a]+"d=(base/'core-perf/opening-light-count').resolve();d.mkdir(exist_ok=True)\n"+src[b:]
    a=src.index('names=');b=src.index('\ns=s[:s.index',a)
    src=src[:a]+"""names=['recomp_0044.c']
(d/names[0]).write_text(transform((base/'gen'/names[0]).read_text()))
"""+src[b:]
    a=src.index('s=s.replace(k," c[-1:');b=src.index('\nexec(compile',a)
    src=src[:a]+'''s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)'''+src[b:]
    exec(compile(src,'tree-level-build','exec'),{'transform':transform})
    Path('build/switch-runtime/core-perf/opening-light-count/recomp_0044.c').unlink()
