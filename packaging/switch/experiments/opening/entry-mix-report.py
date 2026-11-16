"""Compare measured device counts and inspect original offline per-function entrance counts."""
from pathlib import Path
from statistics import mean,correlation
import json,re,sys,runpy
base=Path('build/switch-runtime')
rel=base/'history/0.51.0-rc1'
api=runpy.run_path(str(Path(__file__).resolve().parents[2]/'analyze-profile.py'))
w=api['parse_windows']((base/json.loads((rel/'deployment.json').read_text())['hardware_log']).read_text().splitlines())[1,120]
r=[(cpu,draw,ent,poll) for f,wall,cpu,rc,draw,ent,poll in w['cpu'] if 2<=f<=120]
assert len(r)==119
for k,v in [('all',r),('central',sorted(r)[6:-6]),('differences',[tuple(y-x for x,y in zip(a,b)) for a,b in zip(r,r[1:])])]:
 print('hardware',k,len(v),'CPU correlation with draws/entries/polls',*[round(correlation([x[0] for x in v],[x[i] for x in v]),3) for i in (1,2,3)])
if len(sys.argv)>1:
 s=Path(sys.argv[1]).read_text();assert 'verified 120 original demo frames: 0x00000078' in s
 lines=re.findall(r'^\[ENTRY_MIX\] (\d+)([^\n]*)',s,re.M)
 assert [int(f) for f,x in lines]==list(range(1,121))
 rows=[{int(k,16):int(v) for k,v in re.findall(r' (\w+):(\d+)',x)} for f,x in lines if int(f)>1]
 ordered=sorted(rows,key=lambda r:sum(r.values()));lo,hi=ordered[:12],ordered[-12:]
 keys=set().union(*rows)
 def avg(rs,k):return mean(r.get(k,0) for r in rs)
 delta=mean(sum(r.values()) for r in hi)-mean(sum(r.values()) for r in lo)
 print('offline private entries low/high',*[round(mean(sum(r.values()) for r in rs)) for rs in (lo,hi)])
 for k in sorted(keys,key=lambda k:avg(hi,k)-avg(lo,k),reverse=True)[:12]:
  print(hex(k),'low/high/delta share',round(avg(lo,k),1),round(avg(hi,k),1),round((avg(hi,k)-avg(lo,k))/delta,3))
