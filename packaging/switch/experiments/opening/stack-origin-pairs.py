"""Same live ESP, bounded A64 fallthrough, actual addresses for proposed stack spans."""
import contextlib,io,runpy,re,subprocess,sys
from collections import Counter
from pathlib import Path
with contextlib.redirect_stdout(io.StringIO()):
 data=runpy.run_path(str(Path(__file__).with_name('stack-origin-join.py')))
q=data['q'];elf=sys.argv[1];sets=data['sets'];cache=data['cache'];symbols=data['sym']
# Restrict to original check followed by explicit unsigned out-of-range guard.
def guard(ops,pc):
 o,z=ops.get(pc,('','')); m=re.fullmatch(r'w(\d+), \[x27, x(\d+), lsl #2\]',z)
 if o!='ldr' or not m:return
 cmp,arg=ops.get(pc+4,('',''));branch=ops.get(pc+8,('',''))[0]
 regs=arg.split(', ')
 if cmp=='cmp' and len(regs)==2 and regs[1]=='w'+m[1] and branch in ('b.cs','b.hs'):return regs[0],m[2]
 if cmp=='cmp' and len(regs)==2 and regs[0]=='w'+m[1] and branch in ('b.ls',):return regs[1],m[2]
def delta(ops,pc,reg):
 # Follow address from CMP back to current guest ESP. No SP change allowed
 # until the source is reached. No call, conditional, writeback or pair load.
 n=0
 for j in range(1,33):
  o,z=ops.get(pc-j*4,('',''));p=z.split(', ')
  if reg=='w22':return n
  if not o or o.startswith(('b','cb','tb','ret')) or '!' in z or '],' in z or o.startswith('ldp'):return
  if o.startswith('st') or o in ('cmp','cmn','tst','nop'):continue
  if p[0] in ('x22','w22'):return
  if p[0] not in (reg,'x'+reg[1:]):continue
  if o in ('add','sub') and len(p)==3 and re.fullmatch('#(0x[0-9a-f]+|[0-9]+)',p[2]):n+=(1 if o=='add' else -1)*int(p[2][1:],0)
  elif o!='mov' or len(p)!=2:return
  if not re.fullmatch('w[0-9]+',p[1]):return
  reg=p[1]
pairs={}
for fn in {r[0] for batch in sets for r in batch if cache[r[1]]!='other'}:
 a,size=symbols[fn]
 lines=subprocess.check_output(['objdump','-d','--no-show-raw-insn',f'--start-address={a}',f'--stop-address={a+size}',elf],text=True)
 ops={int(pc,16):(op,args.split('//')[0].strip()) for pc,op,args in re.findall(r'^\s*([a-f0-9]+):\s+(\S+)\s*([^\n]*)$',lines,re.M)}
 for _,p,_,_ in (r for batch in sets for r in batch if r[0]==fn and cache[r[1]]!='other'):
  pc=int(p,16);first=guard(ops,pc)
  if not first:continue
  d0=delta(ops,pc,first[0])
  if d0 is None:continue
  pairs[pc]=(d0,None)
  for j in range(3,65):
   at=pc+4*j;o,z=ops.get(at,('',''));args=z.split(', ')
   if not o or o.startswith(('b','cb','tb','ret')) or '!' in z or '],' in z or (not o.startswith('st') and (args[0] in ('w22','x22') or (o=='ldp' and args[1] in ('w22','x22')))):break
   g=guard(ops,at)
   if g:
    d1=delta(ops,at,g[0])
    if d1 is not None:pairs[pc]=(d0,d1)
    break
for i in range(1,5):
 s=(q['d']/f'run-{i}.log').read_text();stats=Counter()
 for (f,depth,p),(g,p2,reg) in zip(re.findall(r'^\[D3D_SCOPE_PC\] (\d+) (\d+) (\w+)$',s,re.M),re.findall(r'^\[OPREG\] (\d+) (\w+) (.*)$',s,re.M)):
  assert (f,p)==(g,p2)
  if int(depth) or not 31<=int(f)<=120 or cache.get(p,'other')=='other':continue
  stats['recognized']+=1;pc=int(p,16)
  if pc not in pairs:continue
  stats['strict guard/address']+=1
  d0,d1=pairs[pc];regs=[int(t,16) for t in reg.split()];sp=regs[22]&0xffffffff
  addr=(sp+d0)&0xffffffff;ea=q['address'](q['ins'][pc][2],regs)
  assert (ea-q['base'])//4==addr>>12
  if d1 is None:continue
  stats['forward neighbor']+=1
  print('candidate',i,q['ins'][pc][0],hex(pc),d0,d1)
  if min(addr,(sp+d1)&0xffffffff)>>12==(max(addr,(sp+d1)&0xffffffff)+3)>>12:
   stats['both four-byte spans fit one page']+=1
 print(i,dict(stats))
