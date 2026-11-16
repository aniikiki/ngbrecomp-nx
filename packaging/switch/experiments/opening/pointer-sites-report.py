"""Resolve counted gate caller PCs, verify the actual call, and recover source kind where possible."""
import bisect,re,struct,sys
from collections import Counter
from pathlib import Path
d=Path('build/switch-runtime/core-perf/opening-pointer-sites')
sy={}
for line in (d/'symbols.txt').read_text().splitlines():
 a,n,_,fn=line.split(maxsplit=3);a,n=int(a,16),int(n,16)
 if n>sy.get(a,(0,''))[0]:sy[a]=(n,fn)
keys=sorted(sy);gate=next(a for a,(_,fn) in sy.items() if fn=='ngb_gate_ngb_guest_pointer')
s=(d/'budget.log').read_text()
assert '[RESULT] status=1 reason=verified 120 original demo frames' in s
exe=(d/'host/replay').read_bytes()
ph=[struct.unpack_from('<IIQQQQQQ',exe,struct.unpack_from('<Q',exe,32)[0]+56*i) for i in range(struct.unpack_from('<H',exe,56)[0])]
for f in (30,120):
 assert f'[POINTER_SITES] {f} lost=0' in s
 ranked=[];groups=Counter();nb=0
 for row in re.findall(r'^\[PS\] '+str(f)+r' (.+)$',s,re.M):
  pc,c,n,*sizes=row.split();pc=int(pc,16);c=int(c);n=int(n);sizes=list(map(int,sizes))
  assert sum(sizes)==c
  seg=next(v for v in ph if v[0]==1 and v[1]&1 and v[3]<=pc<v[3]+v[5]);w=struct.unpack_from('<I',exe,pc-seg[3]+seg[2])[0]
  imm=w&0x3ffffff;target=pc+4*(imm-(1<<26) if imm>=1<<25 else imm)
  assert w>>26==0x25 and target==gate,(hex(pc),hex(w),hex(target))
  a=keys[bisect.bisect_right(keys,pc)-1];l,name=sy[a];assert pc<a+l
  groups[name]+=c;ranked.append((c,name,hex(pc-a),n,sizes));nb+=n
 print(f,'sites',len(ranked),'calls',sum(groups.values()),'requested bytes',nb,'top functions',groups.most_common(6),'top callsites',sorted(ranked,reverse=True)[:10])
