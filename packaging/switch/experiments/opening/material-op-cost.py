"""Count and time child calls only under the expensive middle material list."""
from pathlib import Path
import re,runpy
def transform(s,u):
 a=s.index('void sub_0030BCA0(void)\n{'); b=s.index('\n}',a); t=s[a:b]
 # Restore previous scope across nested model submissions, including unrelated lists.
 k='RECOMP_ABI_CALL(0x0030C240u, sub_0030C240);'
 assert t.count(k)==3
 for ret in ('0030BCDA','0030C064','0030C0BC'):
  key='PUSH32(esp, 0x'+ret+'u); '+k;assert t.count(key)==1
  t=t.replace(key,'PUSH32(esp, 0x'+ret+'u); {unsigned old=mc_scope;mc_scope='+str(int(ret=='0030C064'))+';'+k+'mc_scope=old;}')
 s=s[:a]+t+s[b:]
 a=s.index('void sub_0030C2A0(void)\n{'); b=s.index('\n}',a); t=s[a:b];sites=[]
 def wrap(m):
  i=len(sites);sites.append(i)
  record='if(mc_scope)mc_target(_icall_target);' if 'ICALL' in m[0] else ''
  return '{'+record+'unsigned ep=tree_epoch;unsigned long long tm=mc_scope?tree_begin('+str(i)+'):0;'+m[0]+'if(tm)tree_end('+str(i)+',ep,tm);}'
 t=re.sub(r'RECOMP_(?:ABI_CALL|ICALL_SAFE_AT)\([^;]+?\);',wrap,t)
 assert len(sites)==6
 return 'static unsigned mc_scope;extern void mc_target(unsigned);extern unsigned tree_epoch;extern unsigned long long tree_begin(unsigned);extern void tree_end(unsigned,unsigned,unsigned long long);\n'+s[:a]+t+s[b:]
if __name__=='__main__':runpy.run_path(str(Path(__file__).with_name('model-copy.py')))['build']('material-op-cost',[(False,[28])],transform)
