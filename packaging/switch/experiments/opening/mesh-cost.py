"""Measure inclusive call cost at each actual dispatch site inside the model submitter."""
from pathlib import Path
import re,runpy
def transform(s,u,va="0030BCA0",count=18):
 a=s.index('void sub_'+va+'(void)\n{');b=s.index('\n}',a)
 body=s[a:b];sites=[]
 def wrap(m):
  i=len(sites);sites.append(m[1])
  return m[1]+" {unsigned ep=tree_epoch;unsigned long long t=tree_begin("+str(i)+");"+m[2]+"if(t)tree_end("+str(i)+",ep,t);}"
 body=re.sub(r'(PUSH32\(esp, 0x[0-9A-F]+u\);) (RECOMP_(?:ABI_CALL|ICALL_SAFE_AT)\([^;]+?\);)',wrap,body)
 assert len(set(sites))==len(sites)==count
 return "extern unsigned tree_epoch;extern unsigned long long tree_begin(unsigned);extern void tree_end(unsigned,unsigned,unsigned long long);\n"+s[:a]+body+s[b:]
if __name__=='__main__':runpy.run_path(str(Path(__file__).with_name('model-copy.py')))['build']('mesh-cost',[(False,[28])],transform)
