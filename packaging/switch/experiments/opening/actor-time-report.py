"""Inclusive counter budget, not achievable CPU savings; require every prior observed visit."""
import re
from pathlib import Path
root=Path('build/switch-runtime/core-perf')
def log(d):
 s=(root/('opening-'+d)/'distribution.log').read_text()
 assert '[RESULT] status=1 reason=verified 120 original demo frames' in s
 return s
a,b=log('actor-time'),log('actor-kinds')
for f,n in ((30,30),(120,90)):
 expected=list(map(int,re.search(rf'^\[ACTOR_KINDS\] {f} (.+)$',b,re.M)[1].split()))
 rows=[tuple(map(int,m)) for m in re.findall(rf'^\[ACTOR_TIME\] {f} (\d+) (\d+) (\d+) (\d+) (\d+)$',a,re.M)]
 assert len({k for k,*_ in rows})==len(rows) and sum(bool(x) for x in expected)==len(rows)
 for k,hz,count,pre,t in rows:
  assert count==expected[k] and 0<pre<=t and hz>0
  print(f'{f-n+1}..{f} kind {k} {count/n:g}/frame: prefix {pre*1000/hz/n:.5f}, full {t*1000/hz/n:.5f} host elapsed ms/frame')
