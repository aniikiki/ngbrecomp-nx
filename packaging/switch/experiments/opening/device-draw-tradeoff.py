"""Necessary CPU reductions only. Draw elapsed time bounds, but does not equal, Draw CPU."""
from pathlib import Path
import re
p,=Path('build/switch-runtime/device-logs').glob('0.55.0-wide-*/boot.log')
s=p.read_text()
assert re.findall(r'\[CLOCK\] first=(\d+) cpu_hz=(\d+) gpu_hz=(\d+)',s)[:2]==[('1','1785000000','307200000'),('121','1785000000','307200000')]
windows=[tuple(map(int,v)) for v in re.findall(r'3D scene flips=(\d+) draws=\d+ elapsed_ms=(\d+)',s)[:2]]
assert [n for n,t in windows]==[30,120]
wait=list(map(int,re.findall(r'render_work_ms=\d+ guest_wait_ms=(\d+)',s)[:2]))
for n,t,w in [(30,windows[0][1],wait[0]),(90,windows[1][1]-windows[0][1],wait[1]-wait[0])]:
    print(n,'wall/wait/remaining excess if all recorded wait vanished (ms)',t,w,round(t-w-n*1000/60,2))
rows=[tuple(map(int,v)) for v in re.findall(r'\[DRAW_BOUND\] frame=(\d+) draws=\d+ ticks=(\d+) cpu=(\d+) rc=(\d+)',s)]
assert [f for f,d,c,rc in rows]==list(range(31,121)) and all(d>=0 and c>0 and rc==0 for f,d,c,rc in rows)
# Work in ticks. At 19.2 MHz, 60 Hz gives 320000 ticks per frame.
budget=320000
def threshold(c,d,q):
    # d is only an upper bound. The most favorable possible split has
    # either zero CPU inside Draw, or as much there as the elapsed timer permits.
    d=min(d,c);need=max(0,c-budget)
    r0=need/c
    rd=max(0,(need-q*d)/(c-d)) if c>d else (0 if q*d>=need else float('inf'))
    r=min(r0,rd)
    def best(r):return max(r*c,r*(c-d)+q*d)
    assert best(r)>=need-1e-6 and (r<1e-7 or best(r-1e-7)<need)
    return r
for q in (0,.5,1):
    v=sorted(threshold(c,d,q) for _,d,c,_ in rows)
    print(f'Draw CPU cut {q:.0%}: minimum outside-Draw cut for 45, 81, 90 frames',
          *(f'{100*v[k-1]:.2f}%' for k in (45,81,90)),
          'CPU budget possible at zero outside cut',sum(x==0 for x in v))
    if q==1:
        print('largest necessary cuts (frame, percent)', sorted(
            [(f,round(threshold(c,d,q)*100,2)) for f,d,c,_ in rows],
            key=lambda pair:-pair[1])[:5])
