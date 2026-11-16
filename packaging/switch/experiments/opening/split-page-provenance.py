"""Identify instruction-local roots of sampled x27 page checks, never infer object identity."""
import re,sys,subprocess
from pathlib import Path
from collections import Counter
d=Path('build/switch-runtime/core-perf/opening-split-profile')
elf=sys.argv[1]
saved={int(a,16):(fn,int(off,16),op,arg) for l in (d/'sampled-insns.txt').read_text().splitlines() if len(z:=l.split(None,4))==5 for a,fn,off,op,arg in [z] if fn.startswith('ngb_reg_') and '[x27' in arg}
by=Counter(); detail=Counter(); sites=Counter()
def classify(pc):
 fn,off,op,arg=saved[pc]
 lo=max(pc-off,pc-96)
 out=subprocess.check_output(['objdump','-d','--no-show-raw-insn',f'--start-address={lo}',f'--stop-address={pc+4}',elf],text=True)
 ops=[(int(a,16),o,args.strip()) for a,o,args in re.findall(r'^\s*([0-9a-f]+):\s+(\S+)\s*([^\n]*)$',out,re.M)]
 assert ops[-1]==(pc,op,arg.strip()),ops[-1]
 if not (m:=re.search(r'\[x27, x(\d+),',arg)):return 'fixed table offset'
 r=m[1]
 for _,o,a in reversed(ops[:-1]):
  if o.startswith(('b.','tb','cb')) or o in ('b','bl','blr','br','ret'):break
  if o.startswith('st') and ('!' in a or '],' in a):break
  if o.startswith('st') or o in ('cmp','cmn','tst','ccmp'):continue
  parts=a.split(', ')
  if len(parts)>1 and o.startswith('ldp') and parts[1] in ('x'+r,'w'+r):return 'loaded value'
  if parts[0] not in ('w'+r,'x'+r):continue
  if o.startswith('ld'):return 'loaded value'
  if o in ('lsr','mov','add','sub','and','ubfx') and len(parts)>=2 and re.fullmatch(r'[wx]\d+',parts[1]) and all(t.startswith('#') for t in parts[2:]):
   r=parts[1][1:]
   if 19<=int(r)<=25:return 'via '+['eax','ecx','edx','esp','ebx','esi','edi'][int(r)-19]
   continue
  return 'other producer'
 return 'unresolved'
cache={}
for i in range(1,5):
 s=(d/f'run-{i}.log').read_text()
 for f,a in re.findall(r'^\[FRAME_PC\] (\d+) ([0-9a-f]+)$',s,re.M):
  pc=int(a,16)
  if not 31<=int(f)<=120 or pc not in saved:continue
  if pc not in cache:cache[pc]=classify(pc)
  k=cache[pc];by[k]+=1;detail[i,k]+=1;sites[k,saved[pc][0],saved[pc][1]]+=1
assert sum(by.values())==130,by
print(by);print(sorted(detail.items()))

print('esp total sites / functions',sum(k[0]=='via esp' for k in sites),len({fn for k,fn,_ in sites if k=='via esp'})); print('esp by guest function',Counter({fn:sum(v for (k,n,_),v in sites.items() if k=='via esp' and n==fn) for k,fn,_ in sites if k=='via esp'}).most_common())
