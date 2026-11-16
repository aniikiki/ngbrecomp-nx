"""Only linked calls, not inline code or work inside driver DSOs; PC is the return address."""
from pathlib import Path
from collections import Counter
import re,bisect,sys
alloc='--alloc' in sys.argv
p=Path('build/switch-runtime/core-perf')/('opening-alloc-budget' if alloc else 'opening-bulk-budget')
label='ALLOC' if alloc else 'BULK'
s=(p/'budget.log').read_text()
assert '[RESULT] status=1 reason=verified 120 original demo frames' in s
symbols={}
for line in (p/'symbols.txt').read_text().splitlines():
 a,n,_,fn=line.split(maxsplit=3);a,n=int(a,16),int(n,16)
 if n>symbols.get(a,(0,''))[0]:symbols[a]=n,fn
keys=sorted(symbols)
for f,frames in [(30,30),(120,90)]:
 vals=[];total=Counter()
 for row in re.findall(fr'^\[{label}\] {f} (.+)$',s,re.M):
  pc,k,c,b,n,t,e,u=row.split();pc=int(pc,16)-4;k,c,b,n,t,e,u=map(int,(k,c,b,n,t,e,u))
  j=bisect.bisect_right(keys,pc)-1;name='outside known ELF functions'
  if j>=0 and pc<keys[j]+symbols[keys[j]][0]:name=symbols[keys[j]][1]+f'+{pc-keys[j]:x}'
  vals.append((name,k,c,b,n,t,e,u));total.update(dict(c=c,b=b,n=n,t=t,e=e,u=u))
 assert total['c'] and total['n'] and total['e']
 # HT estimate (time and independent empty-clock samples each selected with p=1/32).
 ms=lambda t,u:(8 if alloc else 32)*(t-u)/1e6/frames
 print(f,'calls/frame',round(total['c']/frames,1),'bytes/frame',round(total['b']/frames),'samples',total['n'],total['e'],'sampled excess ms/frame',round(ms(total['t'],total['u']),4))
 for name,k,c,b,n,t,e,u in sorted(vals,key=lambda x:x[5]-x[7],reverse=True)[:8]:
  print(name,(('new','new[]','delete sized','delete[]') if alloc else ('copy','move','set'))[k],round(c/frames,1),'calls/frame',round(b/frames),'bytes/frame',n,e,'samples',round(ms(t,u),4),'ms/frame')
