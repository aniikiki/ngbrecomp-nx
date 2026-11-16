from pathlib import Path
def transform(s):
    a=s.index('void d3d_orig_003C7490(void)');b=s.index('\n}',a)
    block=s[a:b];k='ecx = 0x1A;\n    edi = ebx;\n    if (!g_df)'
    assert block.count(k)==1
    fast='''ecx = 0x1A;
    edi = ebx;
    if(!g_df && esi>=4096u && edi>=4096u && esi<NGB_RAM_BYTES && edi<NGB_RAM_BYTES &&
       (esi&4095u)+104<=ngb_fast_page_bytes[esi>>12] &&
       (edi&4095u)+104<=ngb_fast_page_bytes[edi>>12] &&
       (esi+104<=edi || edi+104<=esi)){
       memcpy(ngb_fast_ram+edi,ngb_fast_ram+esi,104);esi+=104;edi+=104;
    } else if (!g_df)'''
    return s[:a]+block.replace(k,fast)+s[b:]
if __name__=='__main__':
    p=Path(__file__).parent
    src=(p/'page-hot-o3.py').read_text()
    a=src.index('next_set=');b=src.index('parent=d.parent',a)
    src=src[:a]+"d=(base/'core-perf/opening-paired-copy').resolve();d.mkdir(exist_ok=True)\n"+src[b:]
    a=src.index('names=');b=src.index('\ns=s[:s.index',a)
    src=src[:a]+"""names=['recomp_0044.c']
(d/names[0]).write_text(transform((base/'gen'/names[0]).read_text()))
"""+src[b:]
    a=src.index('s=s.replace(k," c[-1:');b=src.index('\nexec(compile',a)
    src=src[:a]+'''s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)'''+src[b:]
    exec(compile(src,'tree-level-build','exec'),{'transform':transform})
    Path('build/switch-runtime/core-perf/opening-paired-copy/recomp_0044.c').unlink()
