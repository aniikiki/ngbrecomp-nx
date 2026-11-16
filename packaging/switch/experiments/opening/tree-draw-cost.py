"""Measure the seven actual call sites under the two prominent device stack branches."""
from pathlib import Path
import runpy,re
def transform(s,u):
 k=0
 for name,targets in [('001CB3B0',['00308130','0030B020','00307B80','00307B80']),('001CB510',['00308130','0030B020','003078B0'])]:
  a=s.index('void sub_'+name+'(void)\n{');b=s.index('\n}',a)
  pattern=r'RECOMP_ABI_CALL\(0x(\w+)u, sub_\1\);'
  body=s[a:b];assert re.findall(pattern,body)==targets
  def sub(m):
   nonlocal k
   i=k;k+=1
   return '{unsigned epoch=tree_epoch;unsigned long long t=tree_begin('+str(i)+');'+m[0]+'if(t)tree_end('+str(i)+',epoch,t);}'
  s=s[:a]+re.sub(pattern,sub,body)+s[b:]
 return 'extern unsigned tree_epoch;extern unsigned long long tree_begin(unsigned);extern void tree_end(unsigned,unsigned,unsigned long long);\n'+s
if __name__=='__main__':runpy.run_path(str(Path(__file__).with_name('model-copy.py')))['build']('tree-draw-cost',[(True,[16])],transform)
