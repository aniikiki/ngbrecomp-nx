"""Identify exactly which original function bodies an isolated game actor ran."""
from pathlib import Path
import re,sys,collections
log,gen=Path(sys.argv[1]),Path(sys.argv[2]);s=log.read_text()
assert 'verified original combat window' in s
rows=re.findall(r'^\[ACTOR_CODE\] (\d+) (\d+)(.*)$',s,re.M)
assert rows and all(x[2].strip() for x in rows)
calls=collections.Counter(va.upper() for _,_,line in rows for va in line.split())
unknown=set(calls);funcs=[];units=collections.Counter()
for path in gen.glob('recomp_*.c'):
 for m in re.finditer(r'^void ((?:sub_|d3d_orig_)([\dA-F]+))\(void\)\n\{.*?^\}',path.read_text(),re.M|re.S):
  name,va=m[1],m[2]
  if va not in calls:continue
  unknown.discard(va);units[path.name]+=1
  external=re.findall(r'\b(ngb_\w+|d3d_hook|RECOMP_ICALL\w*|RECOMP_ITAIL\w*)\s*\(',m.group())
  funcs.append((va,name,path.name,len(m.group()),calls[va],','.join(sorted(set(external)-{'ngb_guest_block_poll'}))))
assert not unknown,unknown
print(f'{len(rows)} complete actor captures; {len(funcs)} unique functions, {len(units)} units')
for unit,n in sorted(units.items()):print(unit,n)
out=Path(sys.argv[3]);out.write_text('\n'.join('\t'.join(map(str,r)) for r in sorted(funcs))+'\n')
