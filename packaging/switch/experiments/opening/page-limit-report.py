from pathlib import Path
import re,sys,statistics as st
d=Path(sys.argv[1])
tag=sys.argv[2] if len(sys.argv)>2 else 'pagelimit'
for first in (1,31):
 results={}
 for log in sorted(d/f'{tag}-{arm}-{i}.log' for arm in ('original','limit') for i in range(1,5)):
  s=log.read_text();assert '[RESULT] status=1 reason=verified 120 original demo frames' in s
  rows=[tuple(map(int,m)) for m in re.findall(r'^\[OPEN_PAIR\] (\d+) \d+ (\d+) (\d+)$',s,re.M)]
  assert [v[0] for v in rows]==list(range(1,121))
  rows=rows[first-1:];key=log.stem.removeprefix(tag+'-')
  results[key]=st.mean(v[1] for v in rows)/1e6
  print(first,key,round(results[key],4),'ms',sum(v[2] for v in rows),'draws')
 if len(results)==8:
  diffs=[results['original-'+str(i)]-results['limit-'+str(i)] for i in range(1,5)]
  print('paired ms saved',diffs,'mean',st.mean(diffs))
