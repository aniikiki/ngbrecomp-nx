"""Join measured block weights with GCC's source-line attribution, not exclusive timing.
Retain missing/header locations explicitly; don't assign inlined code to an assumed caller.
"""
import re
from pathlib import Path
from collections import Counter
from functools import lru_cache
@lru_cache(None)
def source(path):
 return path.read_text(errors='replace').splitlines() if path.is_file() else []
def analyze(path,u):
 files={};fn='';weight=0;loc=None;cats=Counter();helpers=Counter();sites=Counter()
 for line in path.open():
  s=line.strip()
  if m:=re.match(r'\.file\s+(\d+)\s+"([^"]+)"(?:\s+"([^"]+)")?',s):
   files[int(m[1])]=Path(m[2])/(m[3] or '')
  elif m:=re.match(r'\.loc\s+(\d+)\s+(\d+)\s+',s):
   loc=int(m[1]),int(m[2])
  elif m:=re.fullmatch(r'(\w+):',s):
   fn=m[1];weight=0;loc=None
  elif s.startswith('.size'):fn='';weight=0
  elif m:=re.match(r'// BLOCK \d+, count:(\d+)(.*?) seq:',s):
   weight=int(m[1]) if m[2].strip() in ('','(precise)') else 0
  elif fn and weight and re.match(r'^[a-z]\w*(?:\.\w+)?\s',s):
   f,n=(files.get(loc[0]),loc[1]) if loc else (None,0)
   name=f.name if f else 'unknown'
   if f and not f.is_absolute():f=Path('/work/build/switch-runtime/switch')/f
   lines=source(f) if f else []; stmt=lines[n-1].strip() if 1<=n<=len(lines) else ''
   if name==f'recomp_{u:04}.c':
    cat=next((tag for tag,pat in [('direct guest call','RECOMP_ABI_CALL'),('push','PUSH32'),('pop','POP32'),('block service','ngb_guest_block_poll'),('entry','RECOMP_ENTRY'),('vector','XMM_|xmm'),('memory','MEM(?:8|16|32|64|F)'),('condition','CMP_|goto loc_')] if re.search(pat,stmt)),'other generated line')
   else:cat='header / '+name
   cats[cat]+=weight
   if f and stmt:
    sites[name,n,stmt[:110]]+=weight
    if cat.startswith('header'):helpers[name,stmt[:96]]+=weight
 assert cats and sites and any(k in ('push','memory','vector','entry','condition') for k in cats),cats
 print('unit',u,'weighted instructions by reported source class',cats,flush=True)
 print('header source lines',helpers.most_common(8),'top exact locations',sites.most_common(12),flush=True)
if __name__=='__main__':
 p=Path(__file__).resolve().parent
 s=(p/'retained-call-work.py').read_text().replace("'-fno-reorder-blocks-and-partition'","'-freorder-blocks-and-partition'").replace("'-g0'","'-g1','-gdwarf-4'")
 a=s.index('   fn=None;');b=s.index('  finally:',a)
 exec(compile(s[:a]+'   analyze(out,u)\n'+s[b:s.index("print('unit caller")],'split-source-work','exec'),{'analyze':analyze})
