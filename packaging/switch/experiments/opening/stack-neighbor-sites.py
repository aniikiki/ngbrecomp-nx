"""Screen fallthrough neighbors around actual sampled ESP page loads. Not an equivalence proof."""
import runpy,re,subprocess
from collections import Counter
from pathlib import Path
a=runpy.run_path(str(Path(__file__).with_name('split-page-provenance.py')))
stats=Counter()
for pc,kind in a['cache'].items():
 if kind!='via esp':continue
 fn,off,_,_=a['saved'][pc];start=pc-off
 text=subprocess.check_output(['objdump','-d','--no-show-raw-insn','--disassemble='+fn,a['elf']],text=True)
 ops={int(m[1],16):(m[2],m[3].strip()) for m in re.finditer(r'^\s*([\da-f]+):[ \t]+(\S+)[ \t]*([^\n]*)$',text,re.M)}
 assert ops[pc]==tuple(a['saved'][pc][2:])
 found=False
 for step in (-4,4):
  for j in range(1,65):
   q=pc+j*step
   if q not in ops:break
   o,arg=ops[q]
   if o.startswith(('cb','tb','b.')) or o in ('b','br','bl','blr','ret'):
    # Only follow the fallthrough of an unsigned page guard whose compare
    # uses the value returned by a nearby x27 load. Never cross a call.
    if o not in ('b.cs','b.hs','b.ls','b.cc','b.lo','b.hi') or ops.get(q-4,('',))[0]!='cmp':break
    cmpregs=ops[q-4][1].split(', ')
    if not any(z[0]=='ldr' and '[x27,' in z[1] and z[1].split(', ')[0] in cmpregs for z in (ops.get(q-dist,('','')) for dist in (8,12,16))):break
   if o=='ldr' and re.search(r'\[x27, x\d+, lsl #2\]',arg):
    # Require a locally traceable guest ESP root for the neighbor too.
    if q not in a['saved']:a['saved'][q]=(fn,q-start,o,arg)
    if a['classify'](q)=='via esp':found=True;break
  if found:break
 stats[found]+=a['sites'][kind,fn,off]
print('sample hits with/without another ESP check within 64 instructions, recognized fallthrough only:',dict(stats))
assert sum(stats.values())==62
