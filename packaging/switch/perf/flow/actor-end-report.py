"""Report counts and actual timing; reject partial captures and zero coverage."""
from pathlib import Path
import re,sys
d=Path(sys.argv[1])
def get(name):
 s=(d/(name+'.log')).read_text()
 assert 'verified original combat window' in s,name
 return s
for name in ('actor-clock','actor-stage2'):
 s=get(name)
 for end,n in [(120,90),(1800,120),(1920,120)]:
  rows=[(key,int(ns)) for key,ns in re.findall(r'^\[TASK\] end='+str(end)+r' key=(\w+) ns=(\d+)',s,re.M)]
  assert rows and any(k.startswith('ac00') for k,_ in rows)
  print(name,end,[(k,round(v/1e6/n,4),round(100*v/sum(x for _,x in rows),1)) for k,v in rows if k.startswith('ac00')])
s=get('actor-fork');rows=re.findall(r'^\[NATIVE_ACTOR\] frame=(\d+) actor=(\d+) exit=(\d+) completed=(\d+) writes=(\d+) child_writes=(\d+) diff=(\d+) nonstack=(\d+) missing=(\d+) extra=(\d+) regs=(\d+) tickets=(\d+):(\d+) entries=(\d+):(\d+)',s,re.M)
assert rows and len({int(r[1]) for r in rows})>=8 # Slow diagnostic work may straddle a scene flip.
rows=[list(map(int,row)) for row in rows]
print('isolated native actor calls:',len(rows),'normal exit:',sum(r[2]==0 and r[3]==1 for r in rows),'exact register and memory set/value:',sum(not any(r[6:11]) and r[2]==0 and r[3]==1 for r in rows),'including ticket and entry counts:',sum(not any(r[6:11]) and r[2]==0 and r[3]==1 and r[11]==r[12] and r[13]==r[14] for r in rows))
