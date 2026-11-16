"""Read the same five detailed frames and the other 85 separately; no clock conversion across devices."""
import re,sys,statistics as st
from pathlib import Path
b=Path('build/switch-runtime');d=b/'core-perf/wide-start'
def split(f):return (f-1)%16==9*((f-1)//16)%16
device=next((b/'device-logs').glob('0.55.0-wide-*/boot.log')).read_text()
assert '[CLOCK] first=1 cpu_hz=1785000000 gpu_hz=307200000' in device
rows=[(int(f),int(t)/19200) for f,t in re.findall(r'\[DRAW_BOUND\] frame=(\d+) draws=\d+ ticks=\d+ cpu=(\d+) rc=0',device)][:90]
assert [f for f,t in rows]==list(range(31,121))
for active in (True,False):
 v=[t for f,t in rows if split(f)==active]
 print('hardware detail',active,'n',len(v),'mean CPU ms',round(st.mean(v),3),'above budget',sum(t>1000/60 for t in v))
tag=sys.argv[1] if len(sys.argv)>1 else 'scope-floor'
assert tag in ('scope-floor','scope-floor-confirm')
pairs={}
for i in range(1,5):
 for arm,expected in [('original',7),('limit',0)]:
  p=d/f'{tag}-{arm}-{i}.log'
  if not p.exists():continue
  s=p.read_text()
  if 'reason=verified 120 original demo frames' not in s:continue
  phases=re.findall(r'scene sampled_frames=(\d+)',s);assert int(phases[-1])==expected,(p,phases)
  rows=re.findall(r'^\[OPEN_PAIR\] (\d+) \d+ (\d+) (\d+)$',s,re.M)
  assert [int(f) for f,t,n in rows]==list(range(1,121))
  pairs[i,arm]={int(f):int(t)/1e6 for f,t,n in rows}
for i in range(1,5):
 if (i,'limit') not in pairs or (i,'original') not in pairs:continue
 for active in (True,False):
  delta=[pairs[i,'original'][f]-pairs[i,'limit'][f] for f in range(31,121) if split(f)==active]
  print('host pair',i,'detail stratum',active,'mean CPU saved ms',round(st.mean(delta),4))
