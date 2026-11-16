from pathlib import Path
import re
d=Path('build/switch-runtime/core-perf/opening-rng-correspondence')
for i in (1,2):
 s=(d/f'vm-access-budget-{i}.log').read_text()
 assert 'reason=verified 120 original demo frames' in s
 v=[list(map(int,m.split())) for m in re.findall(r'^\[VM_COST\] (.*)$',s,re.M)]
 assert [x[0] for x in v]==[30,120]
 for (f,total,single,multi,pages,bad,n,t,en,et),length in zip(v,[30,90]):
  assert total==single+multi+bad and pages>=single+multi*2
  print(i,f,'calls/frame',round(total/length,1),'multi/frame',round(multi/length,1),'actual/empty samples',n,en,'corrected host ms/frame',round((t/n-et/en)*total/length/1e6,5) if n and en else None)
