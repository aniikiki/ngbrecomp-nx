"""Direct dispatch at one measured render-tree site, preserving diagnostics and fallback."""
from pathlib import Path
def transform(s):
    key='RECOMP_ICALL_SAFE_AT(_icall_target, _icall_esp, 0x00308D6Cu);'
    assert s.count(key)==1
    targets=[0x001cb510,0x001cb3b0]
    for t in targets:
        assert f'void sub_{t:08X}(void)' in Path('build/switch-runtime/gen/recomp_0016.c').read_text()
    assert 'recomp_func_t recomp_lookup_manual(uint32_t va) { (void)va; return NULL; }' in Path('packaging/switch/runtime/runtime.c').read_text()
    code='if ((_icall_target==0x001CB510u || _icall_target==0x001CB3B0u) && RECOMP_ICALL_IS_CODE(_icall_target)){'+"""
        g_icall_trace[g_icall_trace_idx & (ICALL_TRACE_SIZE-1)] = _icall_target;
        g_icall_trace_idx++; g_icall_count++;
        RECOMP_ICALL_OBSERVE_SITE(0x00308D6Cu,_icall_target);
        RECOMP_ICALL_OBSERVE(_icall_target,RECOMP_ICALL_SEEN_RESOLVED);
        if (_icall_target==0x001CB510u){RECOMP_ABI_CALL(0x001CB510u,sub_001CB510);}
        else {RECOMP_ABI_CALL(0x001CB3B0u,sub_001CB3B0);}
    }else{"""+key+'}'
    return s.replace(key,code)
if __name__=='__main__':
    p=Path(__file__).parent
    src=(p/'page-hot-o3.py').read_text()
    a=src.index('next_set=');b=src.index('parent=d.parent',a)
    src=src[:a]+"d=(base/'core-perf/opening-tree-dispatch').resolve();d.mkdir(exist_ok=True)\n"+src[b:]
    a=src.index('names=');b=src.index('\ns=s[:s.index',a)
    src=src[:a]+"""names=['recomp_0028.c']
(d/names[0]).write_text(transform((base/'gen'/names[0]).read_text()))
"""+src[b:]
    a=src.index('s=s.replace(k," c[-1:');b=src.index('\nexec(compile',a)
    src=src[:a]+'''s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)'''+src[b:]
    exec(compile(src,'tree-level-build','exec'),{'transform':transform})
    Path('build/switch-runtime/core-perf/opening-tree-dispatch/recomp_0028.c').unlink()
