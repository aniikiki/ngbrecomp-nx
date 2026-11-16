"""Keep cold start, render waits and steady CPU clocks distinct."""
import re
from pathlib import Path
b=Path('build/switch-runtime')
device,=(b/'device-logs').glob('0.55.0-wide-*/boot.log')
s=device.read_text().split('3D scene flips=120 ',1)[0]
assert 'cpu_hz=1785000000 gpu_hz=307200000' in s
waits=list(map(int,re.findall(r'render_work_ms=\d+ guest_wait_ms=(\d+)',s)))
assert len(waits)==2
print('Device cumulative guest render-wait ms: first 30',waits[0],'; following 90',waits[1]-waits[0],'; fraction of steady 488ms deficit',round((waits[1]-waits[0])/488,3))
s=(b/'core-perf/opening-first-init/distribution.log').read_text()
assert 'verified 120 original demo frames' in s
rows=[tuple(map(int,m)) for m in re.findall(r'^\[FIRST_INIT\] (\d+) (\d+) (\d+) (\d+) (\d+)$',s,re.M)]
assert [r[0] for r in rows]==[1,2,3,4,30,120]
stage=[tuple(map(int,m)) for m in re.findall(r'^\[INIT_STAGE\] (\d+) (\d+) (\d+) (\d+) (\d+)$',s,re.M)]
assert len(stage)==3 and [r[:3] for r in stage]==[(1,1,i) for i in range(3)]
for _,f,k,wall,cpu in stage[1:]:print('Host initialization through',('','device/resources','thread wrapper')[k],'wall/guest CPU ms',round(wall/1e6,3),round(cpu/1e6,3))
for lo,hi in [(0,1),(1,2),(2,30),(30,120)]:
 end=next(r for r in rows if r[0]==hi);start=next((r for r in rows if r[0]==lo),(0,0,0,0,0))
 print('Host flips',lo+1,'..',hi,'wall/guest CPU ms per flip',*[round((end[i]-start[i])/(hi-lo)/1e6,3) for i in (3,4)])
