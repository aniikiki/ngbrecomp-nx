"""Rank actual opening-trained call edges, using only precise GCC blocks before private gate rewriting."""
from pathlib import Path
from collections import Counter
import re, shlex, subprocess as sp, tempfile, sys
base=Path('/work/build/switch-runtime')
cmds=sp.check_output(['ninja','-t','commands','ngb-startup'],cwd=base/'switch',text=True).splitlines()
folder=sys.argv[1]; assert folder in ('opening-retained-pgo','opening-retained-pgo-local')
d=base/'core-perf'/folder
edges=Counter();static=Counter()
for u in (2,10,16,28,29):
 n=f'recomp_{u:04}.c'
 c=next(shlex.split(x) for x in cmds if x.endswith('/'+n))
 out=d/(n+'.native.s'); assert not out.exists()
 with tempfile.TemporaryDirectory() as td:
  c[c.index('-o')+1]=str(out);c[c.index('-MF')+1]=td+'/deps';c[c.index('-c')]='-S'
  c[1:1]=['-I'+str(d),'-include',str(d/'regs.h')]
  c[-1:-1]=['-g0','-ffixed-x28','-fno-ipa-ra','-fno-optimize-sibling-calls','-fprofile-dir='+str(d/'profiles'),'-fprofile-use','-fno-profile-values','-fprofile-partial-training','-Werror=missing-profile','-Werror=coverage-mismatch','-fno-reorder-blocks-and-partition','-fno-ipa-cp-clone']
  if u in (2,10,16):c[-1:-1]=['-O3','-fno-peel-loops','-fno-loop-unroll-and-jam','--param=max-completely-peel-times=0','-ffp-contract=off','-fno-fast-math','-fno-optimize-sibling-calls']
  if folder.endswith('-local'):c.insert(-1,'-fno-semantic-interposition')
  c.insert(-1,'-dA')
  try:
   sp.run(c,cwd=base/'switch',check=True)
   fn=None;count=0;total=0
   with out.open() as f:
    for line in f:
     if m:=re.fullmatch(r'(\w+):\s*',line):fn=m[1];count=0
     if line.lstrip().startswith('.size'):fn=None;count=0
     if m:=re.match(r'// BLOCK \d+, count:(\d+)(.*?) seq:',line):
      count=int(m[1]) if m[2].strip() in ('','(precise)') else 0
     if fn and count and (m:=re.match(r'\s*(bl|blr)\s+(\S+)',line)):
      dest=(m[2].removesuffix('.localalias') if m[1]=='bl' else '(indirect)')
      edges[u,fn,dest]+=count;static[u,fn,dest]+=1;total+=count
   assert total>0
  finally:out.unlink(missing_ok=True)
print('unit caller callee precise_weight positive_sites')
for k,v in edges.most_common():print(*k,v,static[k])
