"""Exclusive interrupted-PC hits, separately per run; attribute libc mem compares by LR."""
import re,bisect
from pathlib import Path
from collections import Counter
d=Path('build/switch-runtime/core-perf/opening-hot-profile')
symbols={}
for l in (d/'symbols.txt').read_text().splitlines():
 a,n,_,sym=l.split(maxsplit=3);a,n=int(a,16),int(n,16)
 if n>symbols.get(a,(0,''))[0]:symbols[a]=(n,sym)
keys=sorted(symbols)
def name(pc):
 j=bisect.bisect_right(keys,pc)-1
 if j>=0:
  a=keys[j];n,s=symbols[a]
  if pc<a+n:return s
 return ''
runs=[];libs=[]
for i in [1,2]:
 s=(d/f'run-{i}.log').read_text()
 assert '[RESULT] status=1 reason=verified 120 original demo frames' in s
 rows=re.findall(r'^\[FRAME_PC\] (\d+) (\w+)$',s,re.M)
 lr=re.findall(r'^\[FRAME_LR\] (\d+) (\w+) (\w+)$',s,re.M)
 assert rows==[r[:2] for r in lr]
 count,lost=map(int,re.search(r'^\[FRAME_PC_COUNT\] (\d+) (\d+)$',s,re.M).groups())
 assert count==len(rows)
 modules={(f,pc):(Path(m).name,fn) for f,pc,m,fn in re.findall(r'^\[FRAME_MODULE\] (\d+) (\w+) \w+ (\S+) (\S+)$',s,re.M)}
 c=Counter();call=Counter()
 for f,pc,ret in lr:
  if int(f)<31:continue
  m,fn=modules.get((f,pc),('unknown','?'))
  key=name(int(pc,16)) or f'{m}:{fn}'
  c[key]+=1
  if m.startswith('libc.') and ('memcmp' in fn or 'memcpy' in fn):
   call[name(int(ret,16)-4) or 'unknown']+=1
 runs.append(c);libs.append(call);print(i,'31..120 delivered',sum(c.values()),'whole-window lost',lost)
for title,cs in [('exclusive',runs),('libc compare/copy return site',libs)]:
 print(title)
 for k,n in (cs[0]+cs[1]).most_common(16):print(k,cs[0][k],cs[1][k])
