"""Keep whole-function loop counts distinct from the single hardware-selected caller."""
from pathlib import Path
import sys,re
d=Path(sys.argv[1])
def log(n):
 s=(d/(n+'.log')).read_text()
 assert '[RESULT] status=1 reason=verified 120 original demo frames' in s
 return s
rows=[s.split() for s in log('update-loops').splitlines() if s.startswith('[UPDATE_LOOPS]')]
assert [int(x[1]) for x in rows]==list(range(1,121))
for i,label in enumerate(['root','setup','flags','normals','transform'],2):
 n,h,over=(sum(int(x[i].split(':')[j]) for x in rows) for j in range(3))
 assert not over
 print(label,'executions',n,'same key at same slot',h)
print('already correct destinations',sum(int(x[-1]) for x in rows))
for trial,keys in [('update-cost','update-edges'),('update-candidates','candidate-edges')]:
 s=log(trial);edges={int(k):(a,b) for k,a,b in (x.split() for x in (d/(keys+'.txt')).read_text().splitlines())}
 if trial=='update-candidates':
  q=re.search(r'^\[CANDIDATES\] (\d+) (\d+) (\d+) (\d+)$',s,re.M)
  print('first list zeros/nonzeros, second list zeros/nonzeros',q.groups())
 table={int(k):(int(n),int(ns)) for k,n,ns in re.findall(r'^\[UC\] (\d+) (\d+) (\d+)$',s,re.M)}
 print(trial,'outer calls',table[1][0],'instrumented CPU ms/frame',sum(ns for _,ns in table.values())/120e6)
 if trial=='update-cost':
  print('candidate search inclusive ms/frame',sum(table[k][1] for k,(_,fn) in edges.items() if fn.endswith('_0013D330'))/120e6)
 else:assert sum(table[k][0] for k,(_,fn) in edges.items() if fn.endswith('_00140AF0'))==sum(map(int,q.groups()))
