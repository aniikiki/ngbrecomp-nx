"""Map delivered PCs against the exact sampled ELF; store disassembly only for observed addresses."""
from pathlib import Path
from collections import Counter
from bisect import bisect_right
import re,sys,subprocess
d,elf=map(Path,sys.argv[1:])
sym={}
for l in (d/'symbols.txt').read_text().splitlines():
 a,n,_,name=l.split(maxsplit=3);a=int(a,16);n=int(n,16)
 if n>sym.get(a,(0,''))[0]:sym[a]=(n,name)
keys=sorted(sym)
def locate(pc):
 i=bisect_right(keys,pc)-1
 if i<0:return '',0
 a=keys[i];n,fn=sym[a];return (fn,pc-a) if pc<a+n else ('',0)
rows=[];wanted=set();links=[]
for i in range(1,5):
 s=(d/f'run-{i}.log').read_text()
 assert 'reason=verified 120 original demo frames' in s
 calls=re.findall(r'^\[FRAME_PC\] (\d+) ([0-9a-f]+)$',s,re.M)
 total,lost=map(int,re.search(r'^\[FRAME_PC_COUNT\] (\d+) (\d+)$',s,re.M).groups())
 assert len(calls)==total
 print('run',i,'delivered',total,'overrun or lost',lost)
 modules={int(pc,16):lib.split('/')[-1] for pc,lib in re.findall(r'^\[FRAME_MODULE\] \d+ ([0-9a-f]+) [0-9a-f]+ (\S+) ',s,re.M)}
 lr=re.findall(r'^\[FRAME_LR\] (\d+) ([0-9a-f]+) ([0-9a-f]+)$',s,re.M)
 assert [(f,pc) for f,pc,_ in lr]==calls
 for f,pc,ret in lr:
  site=int(ret,16)-4
  if locate(site)[0] and locate(int(pc,16))[0]:
   wanted.add(site);links.append((i,int(f),int(pc,16),site))
 for f,pc in calls:
  addr=int(pc,16);fn,off=locate(addr)
  if fn:wanted.add(addr)
  rows.append((i,int(f),addr,fn,off,modules.get(addr,'unmapped')))
code={}
proc=subprocess.Popen(['objdump','-d','--no-show-raw-insn',elf],stdout=subprocess.PIPE,text=True)
for line in proc.stdout:
 m=re.match(r'^\s*([0-9a-f]+):\s+(\S+)\s*(.*)',line)
 if m and (pc:=int(m[1],16)) in wanted:code[pc]=m[2],m[3]
assert proc.wait()==0 and wanted==code.keys()
def group(op,args,off):
 if op.startswith(('ld','st')):
  if '[x27' in args:return 'x27 page-table memory'
  if '[x26' in args:return 'x26 guest RAM memory'
  if '[x28' in args:return 'x28 register-file memory'
  if '[sp' in args or '[x29' in args:return 'entry save x29/x30' if off==0 and 'x29, x30' in args else 'other stack memory'
  return 'other memory'
 return 'control' if op.startswith(('b.','cb','tb')) or op in ('bl','blr','b','ret','br') else 'arithmetic / other'
for lo,hi in [(1,30),(31,120)]:
 sectors=Counter();func=Counter();categories=Counter();stable=[Counter(),Counter()]
 for i,f,pc,fn,off,module in rows:
  if not lo<=f<=hi:continue
  isguest=bool(re.match(r'^(?:ngb_reg_)?(?:sub_|d3d_orig_)[0-9A-F]+',fn))
  sector=('guest cold body' if '.cold' in fn else 'guest main body') if isguest else 'private checkpoint' if fn=='ngb_reg_checkpoint' else 'other linked code' if fn else module
  sectors[sector]+=1
  if isguest:
   c=group(*code[pc],off);categories[c]+=1;stable[(i-1)%2][c]+=1
  if fn:func[fn]+=1
 print('frames',lo,hi,'delivered',sum(sectors.values()),'sectors',sectors,'guest instruction locations',categories)
 print('by alternate sampling periods',stable,'leading exact linked symbols',func.most_common(16))
with (d/'sampled-insns.txt').open('w') as f:
 for pc,(op,args) in sorted(code.items()):
  name,off=locate(pc);print(hex(pc),name,hex(off),op,args,file=f)

# x30 is not always the immediate caller. Accept only direct calls to the
# observed function's entry; ignore aliases/tail transfers we cannot prove.
for lo,hi in [(1,30),(31,120)]:
 edges=Counter(); leaves=Counter(); counts=Counter()
 for i,f,pc,site in links:
  if not lo<=f<=hi:continue
  op,args=code[site]
  if op!='bl':continue
  target=int(args.split()[0],16);fn,off=locate(pc)
  if target!=pc-off:continue
  caller,_=locate(site);edges[(caller,fn)]+=1;leaves[fn]+=1;counts[i]+=1
 print('frames',lo,hi,'proven direct-call hits by run',counts,'top edges',edges.most_common(12),'top callees',leaves.most_common(12))
