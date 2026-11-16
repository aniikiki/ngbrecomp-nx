from pathlib import Path
import runpy,sys
p=Path(__file__).resolve().parent
wrap=runpy.run_path(str(p/'mesh-cost.py'))['transform']
inner='--inner' in sys.argv
tag,u,addr,n=('task2ae-cost',1,'0002AEB0',25) if '--update' in sys.argv else ('task200-cost',0,'00020040',26) if inner else ('task298-cost',1,'000298F0',12)
runpy.run_path(str(p/'model-copy.py'))['build'](tag,[(False,[u])],lambda s,u:wrap(s,u,addr,n))
