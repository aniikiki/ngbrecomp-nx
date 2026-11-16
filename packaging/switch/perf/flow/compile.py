from pathlib import Path
import subprocess as sp,shlex,concurrent.futures as cf
p=Path('/work/build/switch-runtime'); d=p/'core-perf/task-flow';d.mkdir(parents=True,exist_ok=True);w=p/'switch';gen=p/'gen'
commands=sp.check_output(['ninja','-t','commands','ngb-startup'],cwd=w,text=True).splitlines()
def build(f):
 c=next(shlex.split(l) for l in commands if l.endswith('/'+f.name));out=d/(f.name+'.o')

 c[c.index('-o')+1]=str(out);c[c.index('-MF')+1]=str(out)+'.d'
 c[1:1]=['-fsanitize=thread','--param=tsan-instrument-func-entry-exit=0'];c.insert(-1,'-g0')
 sp.run(c,cwd=w,check=True);print(f.name,flush=True)
files=[gen/f'recomp_{n:04}.c' for n in range(47)]
with cf.ThreadPoolExecutor(2) as ex:list(ex.map(build,files))
