"""Report opening-only CPU estimates and conservative entry-key repeats."""
from pathlib import Path
import re,sys
def read(path):
 s=Path(path).read_text(); assert 'verified 120 original demo frames: 0x00000078' in s
 rows=[list(map(int,x.split()[1:])) for x in s.splitlines() if x.startswith('[PRED] ')]
 assert [r[0] for r in rows]==list(range(1,121))
 return s,rows
for kind,path in zip(['parent','child','inputs'],sys.argv[1:]):
 s,r=read(path);tot=[sum(col) for col in zip(*r)]
 if kind=='inputs':
  print('calls/invalid/duplicate keys/same observed state/same EAX/child zero',*[tot[i] for i in (1,6,7,8,9,10)])
  print(re.findall(r'^\[PRED_KIND\] (.+)$',s,re.M));continue
 k=4 if kind=='parent' else 5
 clock=int(re.search(r'^\[CLOCK_READ\] (\d+)',s,re.M)[1]);n=120
 raw=sum(x[1]*x[k]/x[2] for x in r)/n
 print(kind,'calls/sample',tot[1:3],'clock ns',clock,'gross ms/frame',round(raw/1e6,4),
       'clock-adjusted ms/frame',round((raw-clock*tot[1]/n)/1e6,4))
