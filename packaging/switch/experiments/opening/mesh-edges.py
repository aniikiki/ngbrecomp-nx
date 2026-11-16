"""Train GCC branch probabilities from the first 30 flips; leave the generated comparisons and all exits intact."""
from collections import Counter
from pathlib import Path
import re,runpy
def transform(s,u):
 log=Path('build/switch-runtime/core-perf/opening-mesh-paths/budget.log').read_text()
 assert '[MP_TOTAL] 44 0 0 0' in log and 'verified 120 original demo frames' in log
 paths=[(int(n),int(h),bytes.fromhex(p)) for n,h,p in re.findall(r'^\[MP_PATH\] (\d+) (\d+) ([0-9a-f]+)$',log,re.M)]
 assert len(paths)==44
 order=sorted(paths,key=lambda r:-r[0])
 print('top1/top4 shares:',[(sum(r[j] for r in order[:k]),sum(r[j] for r in paths)) for j in (0,1) for k in (1,4)])
 edges=Counter()
 for n,_,p in paths:
  for x,y in zip(p,p[1:]):edges[x,y]+=n
 a=s.index('void sub_0030BCA0(void)\n{');b=s.index('\n}',a);body=s[a:b]
 labels=re.findall(r'^loc_(\w+): ;',body,re.M);assert len(labels)==88
 lines=[];changed=0;seen=set();i=None
 for l in body.splitlines(keepends=True):
  m=re.match(r'^loc_(\w+): ;',l)
  if m:i=labels.index(m[1])
  m=re.match(r'^(    if \()(.+)(\) goto loc_(\w+);)',l)
  if m:
   assert i not in seen;seen.add(i);target=labels.index(m[4])
   visited=sum(v for (x,y),v in edges.items() if x==i)
   if visited>=30 and target!=i+1:
    assert all(y in (target,i+1) for (x,y),v in edges.items() if x==i and v)
    prob=(edges[i,target]+1)/(visited+2)
    l=l[:m.start(2)]+f'__builtin_expect_with_probability(!!({m[2]}),1,{prob:.9f})'+l[m.end(2):];changed+=1
  lines.append(l)
 print('profiled branches:',changed);assert changed>=15
 return s[:a]+''.join(lines)+s[b:]
if __name__=='__main__':runpy.run_path(str(Path(__file__).with_name('model-copy.py')))['build']('mesh-edges',[(False,[28])],transform)
