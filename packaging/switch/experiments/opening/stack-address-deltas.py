"""Relative addresses on the sampled fallthrough only. This does not authorize branch deletion."""
import re
def deltas(ops,lo,hi):
 # (seed, byte displacement), or ('page', seed, displacement) for LSR32 #12.
 regs={22:(lo-1,0)}; pages={}
 for pc in range(lo,hi+1,4):
  if pc not in ops:regs={22:(pc,0)};continue
  op,t=ops[pc];p=t.split(', ');dst=re.fullmatch(r'[wx](\d+)',p[0])
  if op=='ldr' and (m:=re.search(r'\[x27, x(\d+), lsl #2\]',t)):
   v=regs.get(int(m[1]))
   if v and len(v)==3:pages[pc]=v[1:]
  if op in ('cmp','tst','cmn','ccmp','nop') or op.startswith(('cb','tb','b.')):continue
  if op.startswith('st') and '!' not in t and '],' not in t:continue
  if op in ('bl','blr','br','b','ret') or '!' in t or '],' in t or op.startswith('ldp'):
   regs={22:(pc,0)};continue
  if not dst:regs={22:(pc,0)};continue
  n=int(dst[1]);m=re.fullmatch(r'[wx](\d+)',p[1]) if len(p)>1 else None
  v=regs.get(int(m[1])) if m else None
  imm=re.fullmatch(r'#(0x[0-9a-f]+|\d+)',p[2]) if len(p)==3 else None
  new=None
  if op=='mov' and len(p)==2:new=v
  if v and len(v)==2 and imm:
   k=int(imm[1],0)
   if op in ('add','sub'):new=(v[0],(v[1]+(k if op=='add' else -k))%2**32)
   if op=='lsr' and p[1].startswith('w') and k==12:new=('page',*v)
  if new:regs[n]=new
  elif n==22:regs[n]=(pc,0)
  else:regs.pop(n,None)
 return pages

if __name__=='__main__':
 from pathlib import Path
 src=Path(__file__).with_name('stack-neighbor-sites.py').read_text()
 src=src.replace('found=False','found=False; pairs=[]; seeds=deltas(ops,max(start,pc-512),pc+256)')
 src=src.replace("if a['classify'](q)=='via esp':found=True;break","if a['classify'](q)=='via esp':\n     found=True\n     if q in seeds and pc in seeds and seeds[q][0]==seeds[pc][0]:\n      diff=(seeds[q][1]-seeds[pc][1]+2**31)%2**32-2**31;pairs.append(abs(diff))")
 src=src.replace('  if found:break','')
 src=src.replace(' stats[found]'," if found:hist[min(pairs) if pairs else 'unresolved']+=a['sites'][kind,fn,off]\n stats[found]")
 from collections import Counter
 hist=Counter()
 exec(compile(src,'neighbors','exec'),{'__file__':str(Path(__file__).with_name('stack-neighbor-sites.py')),'deltas':deltas,'hist':hist})
 print('closest proven absolute guest address displacement per matched sample',hist)
