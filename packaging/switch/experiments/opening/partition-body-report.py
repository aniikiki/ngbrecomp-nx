"""Report layout changes only among guest functions observed in the measured workload."""
from pathlib import Path
import re,subprocess,sys
root=Path('build/switch-runtime/core-perf')
a=root/'opening-retained-pgo';b=root/'opening-partition-pgo'
cc=sys.argv[1] if len(sys.argv)>1 else subprocess.check_output(['xcrun','-f','llvm-nm'],text=True).strip()
rows=[l.split() for l in (a/'call-work.txt').read_text().splitlines()[1:]]
sizes={}
for unit in (2,10,16,28,29):
 def table(d):
  t=subprocess.check_output([cc,'-S','--defined-only',str(d/f'recomp_{unit:04}.c.o')],text=True)
  return {k:int(sz,16) for sz,k in re.findall(r'^[0-9a-f]+\s+([0-9a-f]+)\s+[Tt]\s+(\S+)$',t,re.M)}
 orig,new=table(a),table(b)
 for u,fn,callee,n,_ in rows:
  if int(u)==unit and callee=='ngb_checkpoint' and 'ngb_reg_'+fn in orig:
   key='ngb_reg_'+fn;sizes[key]=int(n),orig[key],new[key],new.get(fn+'.cold',0)
assert sizes
split=[k for k,(_,_,_,cold) in sizes.items() if cold]
print('observed named functions',len(sizes),'with cold symbol',len(split),'primary symbol bytes',sum(x[1] for x in sizes.values()),'to',sum(x[2] for x in sizes.values()))
for k,(n,old,new,cold) in sorted(sizes.items(),key=lambda kv:-kv[1][0])[:12]:print(k,n,old,new,cold)
