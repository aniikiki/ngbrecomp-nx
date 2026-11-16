"""Express x86 unordered-or-relation branches as the negated ordered complement."""
from pathlib import Path
def transform(s):
    count=0
    for rel,op in [('<','>='),('<=','>'),('>','<='),('>=','<')]:
        old=f'(_fca {rel} _fcb || (_fca != _fca || _fcb != _fcb))'
        count+=s.count(old);s=s.replace(old,f'!(_fca {op} _fcb)')
    return s,count
if __name__=='__main__':
    p=Path(__file__).parent
    s=(p/'page-hot-o3.py').read_text().replace("'opening-loop-ira' if loop_ira else 'opening-page-next-o3' if next_set else 'opening-page-hot-o3'","'opening-unordered-branch'")
    k='exec(compile(s,\'page-o3\',\'exec\'),{})'
    s=s.replace(k,"""for name in names:
 text,n=transform((base/'gen'/name).read_text())
 print(name,n,flush=True);(d/name).write_text(text)
k=' sp.run(c,cwd=w,check=True)'
s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)
"""+k)
    exec(compile(s,'unordered-branch','exec'),{'transform':transform})
    for f in Path('build/switch-runtime/core-perf/opening-unordered-branch').glob('recomp_*.c'):f.unlink()
