"""Measure only the guards actually emitted by mixed-fast, with owner function VA."""
from pathlib import Path
import re,runpy
fast=runpy.run_path(str(Path(__file__).with_name('mixed-fast.py')))['transform']
def transform(s):
 lines=fast(s).splitlines(True);va=0
 for i,line in enumerate(lines):
  m=re.match(r'void (?:sub_|d3d_orig_)([0-9A-F]+)\(void\)',line)
  if m:va=int(m[1],16)
  if 'uint32_t ms_va=' not in line:continue
  assert va and 'unsigned char *ms_p=' in line
  n=0
  for l in lines[i+1:]:
   if l.startswith('    }else{'):break
   n+=l.split('/*')[0].count('ms_p+')
  assert n>=4
  lines[i]=line.replace('unsigned char *ms_p=',f'if(mh_on)mh_hit({va}u,{n}u);unsigned char *ms_p=')
 return 'extern unsigned mh_on;extern void mh_hit(unsigned,unsigned);\n'+''.join(lines)

if __name__=='__main__':
    p=Path(__file__).parent
    s=(p/'page-hot-o3.py').read_text().replace("compact='--compact-loops' in sys.argv","compact=True").replace("d=d.parent/'opening-compact-loops'","d=d.parent/'opening-mixed-hit'")
    k='exec(compile(s,\'page-o3\',\'exec\'),{})'
    a=s.index('names=[');b=s.index('\n',a);s=s[:a]+"names=['recomp_%04d.c'%u for u in (2,10,16,26)]"+s[b:]
    s=s.replace(k,"""for name in names:
 (d/name).write_text(transform((base/'gen'/name).read_text()))
k=' sp.run(c,cwd=w,check=True)'
s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)
"""+k)
    exec(compile(s,'mixed-hit','exec'),{'transform':transform})
    for f in Path('build/switch-runtime/core-perf/opening-mixed-hit').glob('recomp_*.c'):f.unlink()
