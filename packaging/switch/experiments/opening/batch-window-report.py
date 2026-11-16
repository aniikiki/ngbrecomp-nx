"""Report CPU, elapsed and wait together; never add overlapping metrics."""
import re,sys
from pathlib import Path
from statistics import mean
root=Path('build/switch-runtime/core-perf/wide-start')
def windows(name):
    s=(root/(name+'.log')).read_text()
    assert '[RESULT] status=1 reason=verified 120 original demo frames' in s
    wall=[tuple(map(int,x)) for x in re.findall(r'3D scene window frames=(\d+) ms=(\d+)',s)]
    wait=list(map(int,re.findall(r'3D scene render_work_ms=\d+ guest_wait_ms=(\d+)',s)))
    cpu=[tuple(map(int,x)) for x in re.findall(r'^\[OPEN_PAIR\] (\d+) \d+ (\d+) \d+$',s,re.M)]
    assert [n for n,_ in wall]==[30,90] and len(wait)==2 and [n for n,_ in cpu]==list(range(1,121))
    return [(sum(t for n,t in cpu if lo<=n<=hi)/(hi-lo+1)/1e6,w/(hi-lo+1),q/(hi-lo+1)) for lo,hi,w,q in
            [(1,120,wall[0][1]+wall[1][1],wait[1]),(31,120,wall[1][1],wait[1]-wait[0])]]
for tag in sys.argv[1:]:
    for win,label in enumerate(('1..120','31..120')):
        pairs=[]
        for i in range(1,5):
            a,b=(windows(f'{tag}-{k}-{i}')[win] for k in ('original','limit'))
            pairs.append(tuple(x-y for x,y in zip(a,b)))
        print(tag,label,'saved CPU/wall/wait ms per frame:',*[round(mean(v),4) for v in zip(*pairs)],'pairs:',[tuple(round(v,4) for v in p) for p in pairs])
