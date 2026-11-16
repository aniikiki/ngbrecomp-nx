"""Compare two matched-build ARM bodies; static counts are not executed counts."""
from collections import Counter
from pathlib import Path
import re,subprocess
d=Path('build/switch-runtime/core-perf/opening-setup')
def inspect(prefix):
 out={}
 for f in d.glob('group-'+prefix+'-*.o'):
  s=subprocess.check_output(['objdump','-dr',f],text=True)
  key=None
  for l in s.splitlines():
   m=re.fullmatch(r'[0-9a-f]+ <([^>]+)>:',l)
   if m:
    name=m[1];mt=re.fullmatch(r'(?:ctrl|group)_((?:sub_|d3d_orig_)[A-F0-9]+)',name)
    key=mt[1] if mt else None
    if key:assert key not in out;out[key]=Counter()
   m=re.match(r'\s*[0-9a-f]+:\s+[0-9a-f]{8}\s+(\w+)\s*(.*)',l)
   if not key or not m:continue
   c=out[key];c['insns']+=1
   if m[1]=='ldrh' and '[x27,' in m[2]:c['page_table']+=1
   if m[1] in ('ldr','ldp','str','stp') and '[sp' in m[2]:c['host_stack']+=1
 return out
a,b=map(inspect,('ctrl','alt'));assert a and a.keys()==b.keys()
print(len(a),'functions','control',sum(a.values(),Counter()),'group',sum(b.values(),Counter()))
