from pathlib import Path
import runpy
p=Path(__file__).parent
wrap=runpy.run_path(str(p/'mesh-cost.py'))['transform']
def transform(s,u):
 s=wrap(s,u,'001D6E20',20)
 k='RECOMP_ENTRY(0x001D6E20u);';assert s.count(k)==1
 return s.replace(k,k+' const unsigned watch=MEM32(esp)==0x001D7114u;').replace(' t=tree_begin(', ' t=!watch?0:tree_begin(')
runpy.run_path(str(p/'model-copy.py'))['build']('shader-child',[(True,[16])],transform)
