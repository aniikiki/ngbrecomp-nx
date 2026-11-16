"""Use the decoded command to predict the target, while honoring the live table."""
from pathlib import Path
import re,struct,sys
def transform(s):
    sys.path.insert(0,str(Path.cwd()/'xboxrecomp/tools/abi_analysis'))
    from xbe_min import XbeFile
    xbe=XbeFile(Path('game_files/default.xbe'))
    for va in (0x14A3A0,0x14A3B0,0x14A3C0):
        k=f'uint32_t _jt = MEM32(edx * 4 + 0x{va:X});'
        assert s.count(k)==1
        a=s.index('\n',s.index(k))+1
        arms=s[a:s.index('    g_seh_ebp',a)]
        targets=struct.unpack('<4I',xbe.read_bytes_at_va(va,16))
        assert all(f'if (_jt == 0x{v:08X}u) goto loc_{v:08X};' in arms for v in targets)
        s=s[:a]+'    switch(edx){\n'+''.join(f'    case {i}: if (_jt==0x{v:08X}u) goto loc_{v:08X}; break;\n' for i,v in enumerate(targets))+'    }\n'+s[a:]
    return s
if __name__=='__main__':
    p=Path(__file__).parent
    s=(p/'page-hot-o3.py').read_text().replace("compact='--compact-loops' in sys.argv","compact=True").replace("d=d.parent/'opening-compact-loops'","d=d.parent/'opening-cmd-target'")
    k='exec(compile(s,\'page-o3\',\'exec\'),{})'
    a=s.index('names=[');b=s.index('\n',a);s=s[:a]+"names=['recomp_0010.c']"+s[b:]
    s=s.replace(k,"""for name in names:
 (d/name).write_text(transform((base/'gen'/name).read_text()))
k=' sp.run(c,cwd=w,check=True)'
s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)
"""+k)
    exec(compile(s,'cmd-target','exec'),{'transform':transform})
    Path('build/switch-runtime/core-perf/opening-cmd-target/recomp_0010.c').unlink()
