import sys,subprocess,runpy,shutil
from pathlib import Path
real=subprocess.run
def watch(args,*a,**kw):
 if isinstance(args,list) and '-o' in args and str(args[args.index('-o')+1]).endswith('/idx.elf'):
  args=[args[0],'-Wl,-Map=/audit/linked.map',*args[1:]]
  q=real(args,*a,**kw)
  shutil.copyfile(args[args.index('-o')+1],'/audit/linked.elf')
  sys.exit(0)
 return real(args,*a,**kw)
subprocess.run=watch
f='packaging/switch/experiments/opening/package-retained.py';sys.argv=[f,'--hardware-test','--pipe-attribution','--opening-warm','--texture-preload','--player'];runpy.run_path(f,run_name='__main__')
