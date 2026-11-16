"""Match live guest-stack page observations to the feeding AArch64 instructions."""
import contextlib,io,runpy,sys,subprocess,re
from pathlib import Path
from collections import Counter
with contextlib.redirect_stdout(io.StringIO()):
 q=runpy.run_path(str(Path(__file__).with_name('stack-page-holdout.py')))
d=q['d']; elf=sys.argv[1];sets=q['sets']
sym={n:(int(a,16),int(sz,16)) for a,sz,t,n in (l.split(maxsplit=3) for l in (d/'symbols.txt').read_text().splitlines())}
now=subprocess.check_output(['nm','-nS','--defined-only',elf],text=True)
compiled={r[3]:(int(r[0],16),int(r[1],16)) for l in now.splitlines() if len(r:=l.split(maxsplit=3))==4}
cache={}
for name in {r[0] for batch in sets for r in batch}:
 a,size=sym[name];assert compiled[name]==(a,size),name
 dis=subprocess.check_output(['objdump','-d','--no-show-raw-insn',f'--start-address={a}',f'--stop-address={a+size}',elf],text=True)
 ops={int(pc,16):(op,args.split('//')[0].strip()) for pc,op,args in re.findall(r'^\s*([a-f0-9]+):\s+(\S+)\s*([^\n]*)$',dis,re.M)}
 targets=set()
 for op,args in ops.values():
  if op=='b' or op.startswith(('b.','cb','tb')):
   m=re.search(r'\b([a-f0-9]+) <',args)
   if m:targets.add(int(m[1],16))
 for _,pc,_,_ in (r for batch in sets for r in batch if r[0]==name):
  addr=int(pc,16);op,args=ops[addr]
  assert (name,op,args)==q['ins'][addr],(pc,args)
  dest=re.search(r'\[x27, x(\d+), lsl #2\]',args)[1]
  prev=ops.get(addr-4,('',''));tag='other'
  if addr not in targets and prev[0]=='lsr':
   m=re.fullmatch(r'w'+dest+r', w(\d+), #12',prev[1])
   if m and m[1]=='22':tag='ESP'
   elif m and addr-4 not in targets:
    op2,args2=ops.get(addr-8,('',''))
    if op2 in ('sub','add') and re.fullmatch(r'w'+m[1]+r', w22, #(?:0x[0-9a-f]+|\d+)',args2):tag='ESP+offset'
  if tag=='other':
   # Follow an exact MOV/add/sub affine chain, then page extraction; reject
   # control-flow joins, unknown producers, second load destinations and writeback.
   r='w'+dest;shift=False
   for j in range(1,33):
    at=addr-4*j
    if at+4 in targets or at not in ops:break
    o,z=ops[at];parts=z.split(', ')
    if o in ('b','bl','blr','br','ret') or o.startswith(('b.','cb','tb')) or '!' in z or '],' in z:break
    if o.startswith('st') or o in ('cmp','cmn','tst','ccmp','nop'):continue
    if o.startswith('ldp') and parts[1] in (r,'x'+r[1:]):break
    if parts[0] not in (r,'x'+r[1:]):continue
    if o=='lsr' and len(parts)==3 and parts[2]=='#12' and not shift:shift=True
    elif o=='mov' and len(parts)==2:pass
    elif shift and o in ('add','sub') and len(parts)==3 and re.fullmatch(r'#(?:0x[0-9a-f]+|[0-9]+)',parts[2]):pass
    else:break
    if not re.fullmatch(r'[wx]\d+',parts[1]):break
    r='w'+parts[1][1:]
    if r=='w22':
     if shift:tag='ESP via chain'
     break
  cache[pc]=tag
for batch in sets:
 print('training' if batch is sets[0] else 'holdout',dict(Counter((cache[pc],same) for name,pc,same,f in batch)),flush=True)
