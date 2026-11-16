"""Reuse one 68-byte source for the two material writes of guest 30D630."""
from pathlib import Path
def transform(s):
 a=s.index('loc_0030D693: ;');b=s.index('    MEM32(0x3D83D0) = eax;',a)
 block=s[a:b];assert block.count('/* rep movsd */')==2
 assert block.count('esi = ebx;')==2 and block.count('ecx = 0x11;')==2
 guard="""loc_0030D693: ;
    uint32_t mc_dst=MEM32(0x3D83C8)+0xf00u;
    if (!g_df && ebx>=4096 && ebx<NGB_RAM_BYTES && mc_dst>=4096 && mc_dst<NGB_RAM_BYTES &&
        (ebx&4095u)+68<=ngb_fast_page_bytes[ebx>>12] &&
        (mc_dst&4095u)+68<=ngb_fast_page_bytes[mc_dst>>12] &&
        (ebx+68<=0x977b78 || ebx>=0x977b78+68) &&
        (ebx+68<=mc_dst || mc_dst+68<=ebx)){
        unsigned char material[68];
        eax=MEM32(0x3D83D0);
        memcpy(material,ngb_fast_ram+ebx,68);
        memcpy(ngb_fast_ram+0x977b78,material,68);
        memcpy(ngb_fast_ram+mc_dst,material,68);
        eax |= 0x9000;esi=ebx+68;edi=mc_dst+68;ecx=0;
        _fb=0xf00;_fbs=0xf00;_fa=eax;_fas=(int32_t)eax;
    } else {
"""
 return s[:a]+guard+block.split('loc_0030D693: ;',1)[1]+'    }\n'+s[b:]
if __name__=='__main__':
    p=Path(__file__).parent
    src=(p/'page-hot-o3.py').read_text()
    a=src.index('next_set=');b=src.index('parent=d.parent',a)
    src=src[:a]+"d=(base/'core-perf/opening-material-twin').resolve();d.mkdir(exist_ok=True)\n"+src[b:]
    a=src.index('names=');b=src.index('\ns=s[:s.index',a)
    src=src[:a]+"""names=['recomp_0028.c']
(d/names[0]).write_text(transform((base/'gen'/names[0]).read_text()))
"""+src[b:]
    a=src.index('s=s.replace(k," c[-1:');b=src.index('\nexec(compile',a)
    src=src[:a]+'''s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)'''+src[b:]
    exec(compile(src,'tree-level-build','exec'),{'transform':transform})
    Path('build/switch-runtime/core-perf/opening-material-twin/recomp_0028.c').unlink()
