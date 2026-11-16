"""77270 allocates a 64-byte slot from a fixed 2048-slot array in the guest image."""
from pathlib import Path
def transform(s):
 a=s.index('void sub_00077270(void)\n{');b=s.index('\n}',a)
 t=s[a:b]
 assert t.count('if (CMP_B(_fa, _fb)) goto loc_00077285;')==1
 assert t.count('edi = edi + 0x957100;')==1
 k='ecx = 0x10;\n    if (!g_df)'
 assert t.count(k)==1
 fast="""ecx = 0x10;
    _Static_assert(0x957100u>=0x8000u && 0x957100u+2048u*64u<=NGB_VM_BEGIN,"ordinary image pool");
    if(!g_df && (edi-0x957100u)<=2047u*64u && esi>=4096 && esi<NGB_RAM_BYTES &&
       (esi&4095u)+64u<=ngb_fast_page_bytes[esi>>12] &&
       (esi+64u<=edi || edi+64u<=esi)){
        memcpy(ngb_fast_ram+edi,ngb_fast_ram+esi,64);esi+=64;edi+=64;
    }else if (!g_df)"""
 return s[:a]+t.replace(k,fast)+s[b:]
if __name__=='__main__':
    p=Path(__file__).parent
    src=(p/'page-hot-o3.py').read_text()
    a=src.index('next_set=');b=src.index('parent=d.parent',a)
    src=src[:a]+"d=(base/'core-perf/opening-slot-copy').resolve();d.mkdir(exist_ok=True)\n"+src[b:]
    a=src.index('names=');b=src.index('\ns=s[:s.index',a)
    src=src[:a]+"""names=['recomp_0005.c']
(d/names[0]).write_text(transform((base/'gen'/names[0]).read_text()))
"""+src[b:]
    a=src.index('s=s.replace(k," c[-1:');b=src.index('\nexec(compile',a)
    src=src[:a]+'''s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)'''+src[b:]
    exec(compile(src,'tree-level-build','exec'),{'transform':transform})
    Path('build/switch-runtime/core-perf/opening-slot-copy/recomp_0005.c').unlink()
