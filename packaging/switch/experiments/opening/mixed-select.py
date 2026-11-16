"""Guard straight-line groups with >=4 accesses at >=3 distinct offset/width pairs."""
import runpy
from pathlib import Path
here=Path(__file__).parent
base=runpy.run_path(str(here/'mixed-span.py'))['transform']
import re
targets={'002E4470','001CB730','00143FD0','001D9D20'}
def transform(s):
 def block(m):
  if m[1] not in targets:return m[0]
  _,body=base(m[0],fast=True).split('\n',1)
  assert 'unsigned char *ms_p=' in body
  return body
 return re.sub(r'(?m)^void sub_([0-9A-F]+)\(void\)\n\{[^}]*?(?s:.*?)^\}',block,s)

if __name__=='__main__':
    p=Path(__file__).parent
    s=(p/'page-hot-o3.py').read_text().replace("compact='--compact-loops' in sys.argv","compact=True").replace("d=d.parent/'opening-compact-loops'","d=d.parent/'opening-mixed-select'")
    k='exec(compile(s,\'page-o3\',\'exec\'),{})'
    a=s.index('names=[');b=s.index('\n',a);s=s[:a]+"names=['recomp_%04d.c'%u for u in (10,16,26)]"+s[b:]
    s=s.replace(k,"""for name in names:
 (d/name).write_text(transform((base/'gen'/name).read_text()))
k=' sp.run(c,cwd=w,check=True)'
s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)
"""+k)
    exec(compile(s,'mixed-select','exec'),{'transform':transform})
    for f in Path('build/switch-runtime/core-perf/opening-mixed-select').glob('recomp_*.c'):f.unlink()
