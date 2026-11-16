"""Distinguish native SP traffic from x27 guest-page reads in the same interruptions."""
import re
from pathlib import Path
from collections import Counter
d=Path('build/switch-runtime/core-perf/opening-xdk-pc-scope')
code={}
for l in (d/'sampled-insns.txt').read_text().splitlines():
 pc,fn,offset,op,*args=l.split();code[int(pc,16)]=(fn,int(offset,16),op,' '.join(args).split('//')[0].strip())
bins=Counter();func=Counter();sites=Counter()
for i in range(1,5):
 s=(d/f'run-{i}.log').read_text()
 for f,depth,pc in re.findall(r'^\[D3D_SCOPE_PC\] (\d+) (\d+) (\w+)$',s,re.M):
  if int(depth) or int(f)<=30:continue
  fn,off,op,args=code.get(int(pc,16),('',0,'',''))
  if not re.match(r'(?:ngb_reg_)?(?:sub_|d3d_orig_)',fn) or '[sp' not in args or not op.startswith(('st','ld')):continue
  regs=args.split('[')[0].strip(' ,')
  kind='frame pair' if regs=='x29, x30' else 'ARM callee-saved GPR pair' if re.fullmatch(r'x(?:19|2[0-9]), x(?:19|2[0-9]|30)',regs) else 'SIMD/FP stack access' if re.search(r'\b[qdsbh]\d+',regs) else 'other SP memory'
  bins[kind]+=1;func[kind,fn]+=1;sites[fn,hex(off),op,args]+=1
print(bins);print('owners',func.most_common(14));print('sites',sites.most_common(12))
origins=Counter()
for i in range(1,5):
 s=(d/f'run-{i}.log').read_text()
 ev=re.findall(r'^\[D3D_SCOPE_PC\] (\d+) (\d+) (\w+)$',s,re.M)
 lr=re.findall(r'^\[FRAME_LR\] (\d+) (\w+) (\w+)$',s,re.M)
 assert len(ev)==len(lr)
 for (f,depth,pc),(g,addr,ret) in zip(ev,lr):
  assert (f,pc)==(g,addr)
  if int(depth) or int(f)<=30:continue
  pc=int(pc,16);fn,off,op,args=code.get(pc,('',0,'',''))
  if not re.match(r'(?:ngb_reg_)?(?:sub_|d3d_orig_)',fn) or off or op!='stp' or not args.startswith('x29, x30, [sp'):continue
  parent,_,branch,target=code.get(int(ret,16)-4,('',0,'',''))
  origins[parent if branch=='bl' and int(target.split()[0],16)==pc else '(unproven)']+=1
print('offset-zero STP, caller via matching direct BL',sum(origins.values()),origins.most_common(12))
