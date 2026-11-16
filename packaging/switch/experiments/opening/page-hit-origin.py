"""Within a straight-line block trace the actual table index back to its VA, conservatively."""
from pathlib import Path
import runpy,re,subprocess
from collections import Counter,defaultdict
import sys
q=runpy.run_path(str(Path(__file__).with_name('ira-audit.py')))
by=defaultdict(dict)
for (fn,off),n in q['samples'].items():by[fn][off]=n
counts=Counter();sites=Counter()
def reg(s):
 m=re.fullmatch('[wx]([0-9]+)',s.strip())
 return int(m[1]) if m else None
for u in range(47):
 obj=q['root']/('opening-page-hot-o3' if u in (2,10,16,26,39) else 'opening-full-page')/f'recomp_{u:04}.c.o'
 p=subprocess.Popen(['/opt/devkitpro/devkitA64/bin/aarch64-none-elf-objdump','-d',obj],stdout=subprocess.PIPE,text=True)
 active=False
 for l in p.stdout:
  if l.endswith('>:\n'):
   m=re.match(r'^([0-9a-f]+) <([^>]+)>:',l);active=False
   if m:
    fn=m[2];active=fn in by and fn.startswith(('ngb_reg_sub_','ngb_reg_d3d_orig_'))
    base=int(m[1],16);history=[]
   continue
  if not active:continue
  m=re.match(r'^\s*([0-9a-f]+):\s+[0-9a-f]{8}\s+(\S+)\s*(.*)',l)
  if not m:continue
  addr=int(m[1],16);op=m[2];args=m[3].split('//')[0].strip()
  idx=re.search(r'\[x27, x(\d+), lsl #2\]',args)
  if idx and op=='ldr' and (n:=by[fn].get(addr-base)):
   curr=int(idx[1]);origin='unresolved';seen=False
   for h,oper in reversed(history):
    parts=oper.split(',');dst=reg(parts[0])
    if dst!=curr:continue
    if not seen:
     if h!='lsr' or len(parts)<3 or parts[2].strip() not in ('#12','#0xc'):break
     curr=reg(parts[1]);seen=True
    elif h in ('add','sub','mov') and (h=='mov' or len(parts)==3 and parts[2].strip().startswith('#')):
     curr=reg(parts[1])
    else:break
    if curr==22:origin='guest ESP';break
    if curr in (19,20,21,23,24,25):origin='other guest GPR';break
    if curr is None:break
   counts[origin]+=n;sites[u,fn,origin]+=n
  if op.startswith(('b.','cb','tb')) or op in ('bl','blr','b','br','ret'):history=[]
  else:history=(history+[(op,args)])[-16:]
 assert p.wait()==0
print('table-load samples by locally visible address expression:',counts)
print('unit/function/address expression:',sites.most_common(24))
