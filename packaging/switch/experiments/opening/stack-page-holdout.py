"""Can static scope guide a stack-page fast path? Validate on disjoint runs/frames.
Exclude D3D-marked samples; include indexed lookups only. A page match alone
does not establish mapping validity or the width/offset of the access."""
from pathlib import Path
from collections import Counter
from runpy import run_path
import re
p=Path(__file__).parent
address=run_path(str(p/'outside-operand-report.py'))['address']
d=Path('build/switch-runtime/core-perf/opening-outside-operand')
base,size=next((int(a,16),int(n,16)) for a,n,_,name in (l.split(maxsplit=3) for l in (d/'data-symbols.txt').read_text().splitlines()) if name=='opening_end4')
ins={int(pc,16):(name,op,' '.join(args)) for pc,name,off,op,*args in (l.split() for l in (d/'sampled-insns.txt').read_text().splitlines())}
sets=[[],[]]
for i in range(1,5):
 s=(d/f'run-{i}.log').read_text(); assert 'reason=verified 120 original demo frames' in s
 sc=re.findall(r'^\[D3D_SCOPE_PC\] (\d+) (\d+) (\w+)$',s,re.M);rs=re.findall(r'^\[OPREG\] (\d+) (\w+) (.*)$',s,re.M)
 assert len(sc)==len(rs)>0
 for (f,depth,pc),(g,q,raw) in zip(sc,rs):
  assert (f,pc)==(g,q)
  if int(depth) or not 31<=int(f)<=120:continue
  name,op,args=ins.get(int(pc,16),('','',''))
  if not re.match(r'^(?:ngb_reg_)?(?:sub_|d3d_orig_)[0-9A-F]+',name) or op!='ldr' or not re.search(r'\[x27, [wx]\d+',args):continue
  regs=[int(x,16) for x in raw.split()];ea=address(args,regs)
  assert regs[27]==base and base<=ea<base+size and (ea-base)%4==0
  same=(ea-base)//4==(regs[22]&0xffffffff)>>12
  sets[(i-1)//2].append((name,pc,same,int(f)))
for ix,key in ((0,'function'),(1,'instruction')):
 train,hold=sets
 cnt=Counter(r[ix] for r in train);matches=Counter(r[ix] for r in train if r[2])
 # Fixed admission rule: repeated observations, every one in the current ESP page.
 accept={k for k,n in cnt.items() if n>=2 and n==matches[k]}
 print(key,'training indexed',len(train),'holdout indexed',len(hold),'trained keys',len(accept),'holdout same page',sum(r[2] for r in hold))
 for lo,hi in ((31,60),(61,90),(91,120)):
  subset=[r for r in hold if lo<=r[3]<=hi]
  y=[r for r in subset if r[ix] in accept]
  print(lo,hi,'stack page matches among selected',sum(r[2] for r in y),'/',len(y),'of available stack matches',sum(r[2] for r in subset),'indexed samples',len(subset))
