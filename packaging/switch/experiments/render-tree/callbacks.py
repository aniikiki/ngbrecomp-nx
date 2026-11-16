"""Attribute the entire ordered render tree to its actual callback targets.
Keep normal indirect dispatch, guest context switches and IRQ accounting."""
from pathlib import Path
import shlex, subprocess as sp,sys
w=Path('/work');p=w/'build/switch-runtime';d=p/'core-perf/render-callbacks';d.mkdir(exist_ok=True);perf=w/'packaging/switch/perf'
if sys.argv[1]=='cross':
 n='recomp_0028.c';s=(p/'gen'/n).read_text()
 for site in ['00308D20','00308D6C']:
  old='RECOMP_ICALL_SAFE_AT(_icall_target, _icall_esp, 0x'+site+'u);'
  assert s.count(old)==1
  s=s.replace(old,'unsigned parent=render_enter(_icall_target); '+old+' render_leave(parent);')
 f=d/n;f.write_text('unsigned render_enter(unsigned);void render_leave(unsigned);\n'+s)
 c=next(shlex.split(x) for x in sp.check_output(['ninja','-t','commands','ngb-startup'],cwd=p/'switch',text=True).splitlines() if x.endswith('/'+n))
 o=str(f)+'.o';c[c.index('-o')+1]=o;c[c.index('-MF')+1]=o+'.d';c[-1]=str(f);c.insert(-1,'-g0');sp.run(c,cwd=p/'switch',check=True)
else:
 s=(perf/'tasks.py').read_text()
 a=s.index("out = work /");b=s.index('\nout.mkdir',a);s=s[:a]+"out=work/'render-callbacks'"+s[b:]
 a=s.index('if story:\n    clock')
 s=s[:a]+'''clock += """
unsigned render_enter(unsigned va){unsigned k=task_key;if(k==0x001ca790u || (k>>24)==0xec)task_set(0xec000000u|va);return k;}
void render_leave(unsigned k){task_set(k);}
"""
'''+s[a:]
 s=s.replace("if children:\n    for name in ('0001', '0010', '0016', '0028'):","if True:\n    for name in ('0028',):")
 exec(compile(s,'render-callback-timing','exec'),{'__file__':str(perf/'tasks.py')})
