"""Physical lower bound per frame if the measured Draw span cost zero.
Use same-frame paired thread/wall ticks; never subtract a host trial."""
from pathlib import Path
import re,statistics as st
f,=Path('build/switch-runtime/device-logs').glob('0.55.0-wide-*/boot.log')
s=f.read_text()
assert re.search(r'^\[CLOCK\] first=1 cpu_hz=1785000000 gpu_hz=307200000$',s,re.M)
rows=[tuple(map(int,m)) for m in re.findall(r'\[DRAW_BOUND\] frame=(\d+) draws=(\d+) ticks=(\d+) cpu=(\d+) rc=(\d+)',s)]
assert [r[0] for r in rows]==list(range(31,121)) and all(r[1]>0 and 0<r[2]<r[3] and r[4]==0 for r in rows)
target=1000/60
floor=[(c-t)/19200 for _,_,t,c,_ in rows]
print(f'Measured Draw span free, with all other work unchanged: {sum(x>target for x in floor)}/90 frames still over the CPU budget')
print('Outside-Draw CPU lower bound min/median/mean/max:',*(round(x,3) for x in (min(floor),st.median(floor),st.mean(floor),max(floor))))
for i in (0,30,60):
    a=floor[i:i+30]
    print(f'frames {31+i}..{60+i}: mean outside >= {st.mean(a):.3f} ms, {sum(x>target for x in a)}/30 over budget')
print('mean CPU excess after free Draw, ignoring all waits:',round(st.mean(floor)-target,3),'ms')
