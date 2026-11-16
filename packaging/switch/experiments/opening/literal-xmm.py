"""Keep the guest base assignment, expose literal image addresses to XMM_MEM."""
from pathlib import Path
import re
p=Path(__file__).parent
pattern=re.compile(r'    (e\w\w) = (0x9501(?:40|80));\n((?:    xmm[0-7] = XMM_MEM\(\1(?: \+ 0x[\da-fA-F]+)?\); /\* mov[au]ps \*/\n){4})')
def transform(s):
    def edit(m):
        r,base,body=m.groups()
        assert re.findall(r'XMM_MEM\((.*?)\)',body)==[r,r+' + 0x10',r+' + 0x20',r+' + 0x30']
        return m[0].replace('XMM_MEM('+r,'XMM_MEM('+base+'u')
    s,n=pattern.subn(edit,s);assert n
    print('literal matrix source groups',n,flush=True)
    return s
if __name__=='__main__':
    s=(p/'page-hot-o3.py').read_text().replace("compact='--compact-loops' in sys.argv","compact=True").replace("d=d.parent/'opening-compact-loops'","d=d.parent/'opening-literal-xmm'")
    a=s.index('names=[');b=s.index('\n',a)
    s=s[:a]+"names=[f'recomp_{i:04}.c' for i in (2,10,16,26)]"+s[b:]
    k="exec(compile(s,'page-o3','exec'),{})"
    s=s.replace(k,"for name in names:(d/name).write_text(transform((base/'gen'/name).read_text()))\ns=s.replace(' sp.run(c,cwd=w,check=True)',\" c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n sp.run(c,cwd=w,check=True)\")\n"+k)
    exec(compile(s,'literal-xmm','exec'),{'transform':transform})
    for f in Path('build/switch-runtime/core-perf/opening-literal-xmm').glob('recomp_*.c'):f.unlink()
