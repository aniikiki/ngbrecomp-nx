"""Instrument two original loops by identity of the current actor and phase."""
from pathlib import Path
import shlex,subprocess as sp,sys
p=Path('/work/build/switch-runtime');w=p/'switch';d=p/'core-perf/actor-flow';d.mkdir(exist_ok=True)
consume='--consume' in sys.argv
if consume:d=p/'core-perf/actor-consume';d.mkdir(exist_ok=True)
commands=sp.check_output(['ninja','-t','commands','ngb-startup'],cwd=w,text=True).splitlines()
for unit,begin,end,stage in [(16,'loc_001CC5F0: ; ngb_guest_block_poll();','loc_001CC62B: ;',1),(10,'loc_00147ECD: ;','loc_00147EE6: ;',2)]:
 name=f'recomp_{unit:04}.c';s=(p/'gen'/name).read_text()
 for k in (begin,end):assert s.count(k)==1
 s='void actor_begin(unsigned,unsigned,unsigned);void actor_end(void);\n'+s.replace(begin,begin+f' actor_begin({stage},edi,esp);').replace(end,end+' actor_end();')
 if consume and unit==10:
  tag='actor_begin(2,edi,esp);';s='int actor_replay(void);\n'+s.replace(tag,tag+' if(actor_replay())goto loc_00147EE6;')
 path=d/name;path.write_text(s)
 c=next(shlex.split(x) for x in commands if x.endswith('/'+name));o=str(path)+'.o';c[c.index('-o')+1]=o;c[c.index('-MF')+1]=o+'.d';c[-1]=str(path);c[1:1]=['-fsanitize=thread','--param=tsan-instrument-func-entry-exit=0','-g0'];sp.run(c,cwd=w,check=True)
