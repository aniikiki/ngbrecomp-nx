"""Sample the whole script caller OR its command subcall on alternating invocations.
No nested clock instrumentation in the measured caller population."""
from pathlib import Path
import runpy
p=Path(__file__).parent
def transform(s,u):
 a=s.index('void sub_00016270(void)\n{');b=s.index('\n}',a)
 v=s[a:b];k='RECOMP_ENTRY(0x00016270u);'
 v=v.replace(k,k+''' static unsigned chooser=241; chooser=chooser*1664525u+1013904223u;
 unsigned subonly=chooser>>31,epoch=tree_epoch;unsigned long long outer=subonly?0:tree_begin(0);''')
 k='RECOMP_ABI_CALL(0x00016300u, sub_00016300);';assert v.count(k)==1
 v=v.replace(k,'{unsigned ep=tree_epoch;unsigned long long ct=subonly?tree_begin(1):0;'+k+'if(ct)tree_end(1,ep,ct);}')
 assert v.count('return;')==1
 return 'extern unsigned tree_epoch; extern unsigned long long tree_begin(unsigned);extern void tree_end(unsigned,unsigned,unsigned long long);\n'+s[:a]+v.replace('return;','if(outer)tree_end(0,epoch,outer);return;')+s[b:]
if __name__=='__main__':runpy.run_path(str(p/'model-copy.py'))['build']('script-loop-cost',[(False,[0])],transform)
