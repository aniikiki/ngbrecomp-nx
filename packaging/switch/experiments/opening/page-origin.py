"""Conservative local provenance of the sampled private-ABI x27 page-table index."""
from pathlib import Path
from collections import Counter
import re,subprocess
base=Path('build/switch-runtime')
d=base/'core-perf/opening-setup'
rows=[l.split('\t') for l in (d/'leaf-budget.tsv').read_text().splitlines() if '\t' in l]
nro=(base/'history/0.51.0-rc1/ngb-startup.nro').open('rb')
def provenance(pc):
 out=subprocess.check_output(['objdump','-d','--start-address='+hex(pc-80),'--stop-address='+hex(pc+4),base/'native-regs/ngb-startup.elf'],text=True)
 ops=[]
 for m in re.finditer(r'^\s*([\da-f]+):\s+([\da-f]{8})[ \t]+(\S+)[ \t]*([^\n]*)',out,re.M):
  address=int(m[1],16);nro.seek(address);assert nro.read(4)==bytes.fromhex(m[2])[::-1]
  ops.append((m[3],m[4].split('//')[0].strip()))
 assert len(ops)==21
 # Trace only register moves, fixed displacements, shifts and literal constants.
 # Stop at any branch/call, load, or unrecognized producer. This is local
 # instruction evidence, not a proof of the dynamic target address.
 m=re.search(r'\[x27, x(\d+)',ops[-1][1])
 if not m:return 'unknown'
 reg=m[1]
 for op,arg in reversed(ops[:-1]):
  if op.startswith(('b.','cb','tb')) or op in ('b','bl','blr','br','ret'):break
  parts=arg.split(', ')
  if parts[0] not in ('w'+reg,'x'+reg):continue
  if op in ('lsr','lsl','ubfx','and','sub','add','mov') and len(parts)>=2 and re.fullmatch(r'[wx]\d+',parts[1]) and all(x.startswith('#') for x in parts[2:]):
   reg=parts[1][1:]
   if reg=='22':return 'guest SP-derived'
  elif op=='mov' and len(parts)>1 and parts[1].startswith('#'):return 'immediate'
  elif op.startswith('ldr'):return 'loaded pointer/index'
  else:break
 return 'unresolved'
stats=Counter()
for row in rows:
 if row[4]!='guest page-table load':continue
 key=provenance(int(row[2],16));stats[key]+=1
 print(row[0],row[2],row[3],key)
print(stats)
