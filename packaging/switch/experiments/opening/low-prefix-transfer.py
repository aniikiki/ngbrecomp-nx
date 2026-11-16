"""Out-of-run test: how many captured table loads even recur at a trained machine-code site?"""
from pathlib import Path
from bisect import bisect_right
from collections import Counter,defaultdict
import re
d=Path('build/switch-runtime/core-perf/opening-low-prefix-sample')
sym={}
for row in (d/'symbols.txt').read_text().splitlines():
 a,n,_,name=row.split(maxsplit=3);a,n=int(a,16),int(n,16)
 if n>sym.get(a,(0,''))[0]:sym[a]=n,name
keys=sorted(sym)
def capture(i):
 log=(d/f'run-{i}.log').read_text();assert 'verified 120 original demo frames' in log
 rows=[]
 for f,pc,page,end in re.findall(r'^\[LOW_PREFIX\] (\d+) (\w+) (\w+) (\w+)$',log,re.M):
  if not 31<=int(f)<=120:continue
  pc,page,end=[int(x,16) for x in (pc,page,end)];j=bisect_right(keys,pc)-1
  if j<0:continue
  a=keys[j];n,name=sym[a]
  if pc<a+n and name.startswith(('ngb_reg_sub_','ngb_reg_d3d_orig_')):
   rows.append((name,pc-a,'prefix' if 8<=page<end else 'stack window' if 0x1180<=page<0x11e9 else 'elsewhere'))
 return rows
a,b=capture(1),capture(2)
for train,test in ((a,b),(b,a)):
 for kind in ('pc','function'):
  key=lambda row:row[:2] if kind=='pc' else row[:1]
  rules=defaultdict(set)
  for row in train:rules[key(row)].add(row[-1])
  score=Counter()
  for row in test:
   seen=rules.get(key(row),set())
   label='unseen' if not seen else 'ambiguous' if len(seen)!=1 else 'matched' if row[-1] in seen else 'changed'
   score[label]+=1
  print(kind,len(train),'training samples ->',len(test),'held-out samples:',dict(score))
