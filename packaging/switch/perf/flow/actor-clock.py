"""Measure the two loop bodies in thread CPU ms (not RAM-op units).
Worker switches and nested hardware callbacks get their own clocks."""
from pathlib import Path
import sys,shlex,subprocess as sp
root=Path('/work');p=root/'build/switch-runtime';perf=root/'packaging/switch/perf';d=p/'core-perf/actor-clock';d.mkdir(exist_ok=True)
if sys.argv[1]=='cross':
 w=p/'switch';commands=sp.check_output(['ninja','-t','commands','ngb-startup'],cwd=w,text=True).splitlines()
 for unit,b,e,i in [(16,'loc_001CC5F0: ; ngb_guest_block_poll();','loc_001CC62B: ;',1),(10,'loc_00147ECD: ;','loc_00147EE6: ;',2)]:
  name=f'recomp_{unit:04}.c';s=(p/'gen'/name).read_text();assert all(s.count(k)==1 for k in [b,e])
  tag='void sub_'+('001CC5A0' if i==1 else '00147DF0')+'(void)\n{';s=s.replace(tag,tag+'\n unsigned prior_actor_clock=0;')
  s='unsigned actor_clock(unsigned);void actor_unclock(unsigned);\n'+s.replace(b,b+f' prior_actor_clock=actor_clock({i});').replace(e,e+' actor_unclock(prior_actor_clock);');path=d/name;path.write_text(s)
  c=next(shlex.split(x) for x in commands if x.endswith('/'+name));o=str(path)+'.o';c[c.index('-o')+1]=o;c[c.index('-MF')+1]=o+'.d';c[-1]=str(path);c.insert(-1,'-g0');sp.run(c,cwd=w,check=True)
else:
 s=(perf/'tasks.py').read_text().replace("out = work / ('story-tasks' if story else 'task-children' if children else 'tasks')","out = work / 'actor-clock'")
 s=s.replace("if story:\n    clock =",'''clock += """
unsigned actor_clock(unsigned stage){unsigned old=task_key;task_set(0xac000000+stage);return old;}
void actor_unclock(unsigned old){task_set(old);}
"""
if story:
    clock =''')
 s=s.replace("if children:\n    for name in ('0001', '0010', '0016', '0028'):","if True:\n    for name in ('0010','0016'):")
 exec(compile(s,'actor-clock-link','exec'),{'__name__':'__main__','__file__':str(perf/'tasks.py')})
