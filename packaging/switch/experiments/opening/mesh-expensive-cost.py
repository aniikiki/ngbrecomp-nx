"""Split the pre-record path by real call site inside the disproportionately costly part loop."""
from pathlib import Path
import runpy,sys
exp_setup="--expensive-setup" in sys.argv
setup=exp_setup or "--common-setup" in sys.argv
common=setup or "--common" in sys.argv
p=Path(__file__).parent
m=runpy.run_path(str(p/'mesh-cost.py'))
def transform(s,u):
 if setup:
  s=m['transform'](s,u,'0030B7E0',13)
  k='RECOMP_ENTRY(0x0030BCA0u);'
  assert s.count(k)==1
  s=s.replace(k,k+' const unsigned common_site=MEM32(esp)=='+('0x00307C61u;' if exp_setup else '0x003079CCu;'))
  k='RECOMP_ABI_CALL(0x0030B7E0u, sub_0030B7E0);'
  a=s.index('void sub_0030BCA0(void)\n{');b=s.index('\n}',a)
  assert s[a:b].count(k)==1
  s=s[:a]+s[a:b].replace(k,'{ unsigned saved=common_setup; common_setup=common_site; '+k+' common_setup=saved; }')+s[b:]
  a=s.index('void sub_0030B7E0(void)\n{');b=s.index('\n}',a)
  assert s[a:b].count('t=tree_begin(')==13
  import re
  return 'static unsigned common_setup;\n'+s[:a]+re.sub(r't=tree_begin\((\d+)\);',r't=common_setup?tree_begin(\1):0;',s[a:b])+s[b:]
 s=m['transform'](s,u)
 k='RECOMP_ENTRY(0x0030BCA0u);'
 assert s.count(k)==1
 s=s.replace(k,k+' const unsigned measured_parent=MEM32(esp)=='+('0x003079CCu' if common else '0x00307C61u')+';')
 a=s.index('void sub_0030BCA0(void)\n{');b=s.index('\n}',a)
 body=s[a:b];assert body.count('t=tree_begin(')==18
 import re
 body=re.sub(r't=tree_begin\((\d+)\);',r't=measured_parent?tree_begin(\1):0;',body)
 return s[:a]+body+s[b:]
runpy.run_path(str(p/'model-copy.py'))['build']('mesh-expensive-setup' if exp_setup else 'mesh-common-setup' if setup else 'mesh-common-cost' if common else 'mesh-expensive-cost',[(False,[28])],transform)
