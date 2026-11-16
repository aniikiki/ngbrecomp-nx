"""Disjoint guest-thread leaf samples by register-domain membership. Distinguish
a saved frame from a direct caller of a possibly frameless libc leaf. The NRO
at the saved address must have a direct BL to that function to claim a site."""
from collections import Counter
from pathlib import Path
import re,json,runpy
root=Path('build/switch-runtime');h=root/'history/0.51.0-rc1'
api=runpy.run_path('packaging/switch/analyze-profile.py')
name=api['load_symbols'](h/'symbols.gz')
w=api['parse_windows']((root/json.loads((h/'deployment.json').read_text())['hardware_log']).read_text().splitlines())[1,120]
def symbols(path):
 return set(re.findall(r'^\.global (\w+)$',path.read_text(),re.M))
old=symbols(root/'native-regs/entry.S');full=symbols(root/'core-perf/opening-full-guest/entry.S')
assert len(old)==3500 and len(full)==11579 and old<=full
rows=[x for x in w['profiles']['guest'][1] if 31<=x[0]<=120]
known=Counter(); extra=Counter();calls=Counter()
with (h/'ngb-startup.nro').open('rb') as nro:
 for fr,worker,scope,wall,cpu,pcs in rows:
  leaf=name(pcs[0]);fn=leaf.removeprefix('ngb_reg_').split('.')[0]
  if fn in old: bucket='already in 14 (incl wrappers)'
  elif fn in full: bucket='newly covered 33 (incl wrappers)';extra[fn]+=1
  elif leaf.startswith('ngb_gate_') or leaf in ('ngb_reg_checkpoint','ngb_checkpoint'):bucket='gates / checkpoints'
  else:bucket='outside guest units'
  known[bucket]+=1
  if leaf not in ('memcmp','memset','memcpy','memmove'):continue
  if len(pcs)<2:calls[leaf,'no frame']+=1;continue
  pc=pcs[1];nro.seek(pc);ins=int.from_bytes(nro.read(4),'little')
  if ins>>26==0b100101:
   delta=((ins&0x3ffffff)^0x2000000)-0x2000000
   if name(pc+4*delta)==leaf:
    calls[leaf,'direct BL: '+name(pc)+' @ '+hex(pc)]+=1;continue
  calls[leaf,'no verified direct call in top frame']+=1
print('0.51.0-rc1 device, 31..120, guest wall samples:',len(rows),dict(known))
print('newly covered samples:',extra.most_common())
print('byte primitive direct sites:',calls.most_common())
