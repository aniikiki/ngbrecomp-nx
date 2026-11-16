"""Compare completed per-search observations across callers in six original demo frames."""
from collections import Counter
from pathlib import Path
log=Path('build/switch-runtime/core-perf/opening-node-family/budget.log').read_text()
assert '[RESULT] status=1 reason=verified 120 original demo frames' in log
frames=[]
for line in log.splitlines():
 if not line.startswith('[NODE_FAMILY] '):continue
 _,frame,total,*records=line.split()
 assert int(total)==len(records)<=1024
 frames.append(int(frame))
 histories={n:{} for n in (16,64,256,1024)};saved=Counter()
 groups=[Counter() for _ in range(3)]
 for r in records:
  family,h,k,n,ptrs,values=r.split(':')
  for cap,cache in histories.items():
   key=(h,k); value=(n,ptrs,values)
   previous=cache.pop(key,None)
   if previous and previous[0]!=family and previous[1]==value:saved[cap]+=int(n)
   cache[key]=(family,value)
   if len(cache)>cap:del cache[next(iter(cache))]
  if int(n):groups[int(family)][h,k,int(n),ptrs,values]+=1
 print(frame,'nonempty searches',*[sum(g.values()) for g in groups])
 print('cross-owner previously matched node visits by lookup-start order',dict(saved))
 for i,j in [(0,1),(0,2),(1,2)]:
  common=groups[i]&groups[j]
  print(i,j,'matching path fingerprints',sum(common.values()),'compared nodes',sum(key[2]*v for key,v in common.items()))
assert frames==[1,30,31,60,90,120],frames
