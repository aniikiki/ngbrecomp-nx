"""Accept magnitudes through 2^31; preserve the lower bound and finite-input checks."""
from pathlib import Path
def transform(s):
 k='vcleq_u32(mag, vdupq_n_u32(157u << 23))'
 assert s.count(k)==1
 return s.replace(k,k.replace('157u','158u'))
if __name__=='__main__':
    p=Path(__file__).parent
    s=(p/'page-hot-o3.py').read_text().replace("compact='--compact-loops' in sys.argv","compact=True").replace("d=d.parent/'opening-compact-loops'","d=d.parent/'opening-row-ceiling'")
    k='exec(compile(s,\'page-o3\',\'exec\'),{})'
    a=s.index('names=[');b=s.index('\n',a);s=s[:a]+"names=['recomp_%04d.c'%u for u in (39,)]"+s[b:]
    s=s.replace(k,"""for name in names:
 (d/name).write_text((base/'gen'/name).read_text())
 (d/'arm_math.h').write_text(transform(Path('packaging/switch/runtime/arm_math.h').read_text()))
k=' sp.run(c,cwd=w,check=True)'
s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)
"""+k)
    exec(compile(s,'row-ceiling','exec'),{'transform':transform})
    for f in Path('build/switch-runtime/core-perf/opening-row-ceiling').glob('recomp_*.c'):f.unlink()
