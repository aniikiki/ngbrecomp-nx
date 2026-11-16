"""Keep exact endpoints and zero exception; replace two unsigned bounds tests with one."""
from pathlib import Path
def transform(s):
 old="""vandq_u32(vcgeq_u32(mag, vdupq_n_u32(97u << 23)),
                               vcleq_u32(mag, vdupq_n_u32(157u << 23)))"""
 assert s.count(old)==1
 return s.replace(old,"vcleq_u32(vsubq_u32(mag,vdupq_n_u32(97u<<23)),vdupq_n_u32(60u<<23))")
if __name__=='__main__':
    p=Path(__file__).parent
    s=(p/'page-hot-o3.py').read_text().replace("compact='--compact-loops' in sys.argv","compact=True").replace("d=d.parent/'opening-compact-loops'","d=d.parent/'opening-row-range'")
    k='exec(compile(s,\'page-o3\',\'exec\'),{})'
    a=s.index('names=[');b=s.index('\n',a);s=s[:a]+"names=['recomp_%04d.c'%u for u in (39,)]"+s[b:]
    s=s.replace(k,"""for name in names:
 (d/name).write_text((base/'gen'/name).read_text())
 (d/'arm_math.h').write_text(transform(Path('packaging/switch/runtime/arm_math.h').read_text()))
k=' sp.run(c,cwd=w,check=True)'
s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)
"""+k)
    exec(compile(s,'row-range','exec'),{'transform':transform})
    for f in Path('build/switch-runtime/core-perf/opening-row-range').glob('recomp_*.c'):f.unlink()
