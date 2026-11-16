"""Use one full-span check for the adjacent flag and slot in a live light record."""
from pathlib import Path
def transform(s):
    a=s.index('loc_003C78C1: ;');b=s.index('loc_003C78E8: ;',a)
    body=s[a:b]
    begin=body.index('    edi = MEM32(eax + ebx + 0x68);')
    end=body.index('    if (CMP_EQ',begin)
    old=body[begin:end]
    assert old.count('MEM32(')==3
    fast=old.replace('edi = MEM32(eax + ebx + 0x68);','__builtin_memcpy(&light_flags, light_ptr, 4); edi=light_flags;').replace('ecx = MEM32(eax + ebx + 0x8C);','__builtin_memcpy(&light_slot, light_ptr+36, 4); ecx=light_slot;').replace('MEM32(eax + 0x68) = edi;','light_flags=edi; __builtin_memcpy(light_ptr,&light_flags,4);')
    return s[:a]+body[:begin]+"""    {
    uint32_t light_addr = eax + ebx + 0x68u;
    if ((light_addr & 4095u)+40u <= ngb_fast_page_bytes[light_addr>>12]) {
        unsigned char *light_ptr = ngb_fast_ram+(light_addr & 0x7fffffffu);
        uint32_t light_flags, light_slot;
"""+fast+'    } else {\n'+old+'    }\n    }\n'+body[end:]+s[b:]
if __name__=='__main__':
    p=Path(__file__).parent
    src=(p/'page-hot-o3.py').read_text()
    a=src.index('next_set=');b=src.index('parent=d.parent',a)
    src=src[:a]+"d=(base/'core-perf/opening-light-record').resolve();d.mkdir(exist_ok=True)\n"+src[b:]
    a=src.index('names=');b=src.index('\ns=s[:s.index',a)
    src=src[:a]+"""names=['recomp_0044.c']
(d/names[0]).write_text(transform((base/'gen'/names[0]).read_text()))
"""+src[b:]
    a=src.index('s=s.replace(k," c[-1:');b=src.index('\nexec(compile',a)
    src=src[:a]+'''s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)'''+src[b:]
    exec(compile(src,'tree-level-build','exec'),{'transform':transform})
    Path('build/switch-runtime/core-perf/opening-light-record/recomp_0044.c').unlink()
