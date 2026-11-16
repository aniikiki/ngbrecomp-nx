"""Compare actual completed Vulkan scanouts, in order, without storing any frame dumps."""
import re
from pathlib import Path
d=Path('build/switch-runtime/core-perf/opening-present-combined')
def read(arm):
    s=(d/f'recipepixels-{arm}-1.log').read_text()
    assert 'verified 120 original demo frames' in s and '[IDLE_DEVICE] adopted at scene start' in s
    rs=[(int(i),h) for i,h in re.findall(r'^\[OPEN_PIXELS\] (\d+) ([0-9a-f]{8})$',s,re.M)]
    assert [i for i,_ in rs]==list(range(len(rs))) and len(rs)>100, len(rs)
    assert len(set(h for _,h in rs))>20
    return [h for _,h in rs]
a,b=read('base'),read('warm')
diff=[i+1 for i,(x,y) in enumerate(zip(a,b)) if x!=y]
print('completed images base/warm',len(a),len(b),'matching CRC32 in order',min(len(a),len(b))-len(diff),'first differing scanouts',diff[:10])
if not diff and len(a)==len(b): print('Every completed scanout matched.')
else:raise SystemExit('Pixel parity is unconfirmed; do not promote.')
