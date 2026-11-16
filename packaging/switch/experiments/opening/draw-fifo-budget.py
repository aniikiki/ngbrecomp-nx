"""Optimistic same-work additive credit, allowing even double counting of overlaps."""
from pathlib import Path
import re
p,=Path('build/switch-runtime/device-logs').glob('0.55.0-wide-*/boot.log')
s=p.read_text()
assert '[CLOCK] first=1 cpu_hz=1785000000 gpu_hz=307200000' in s
parts=re.split(r'3D scene flips=(\d+) draws=\d+ elapsed_ms=(\d+)',s)
windows={}
for i in range(1,len(parts),3):
 f=int(parts[i]); m=re.findall(r'3D scene cumulative fifo_ms=(\d+)',parts[i-1]);assert len(m)==1
 if f in (30,120) and f not in windows and m:windows[f]=(int(parts[i+1]),int(m[0]),parts[i+2])
rows=[tuple(map(int,n)) for n in re.findall(r'\[DRAW_BOUND\] frame=(\d+) draws=\d+ ticks=(\d+) cpu=(\d+) rc=0',windows[120][2])]
assert [n[0] for n in rows]==list(range(31,121))
# FIFO cumulative ms is integer-truncated; allow 1 ms over the whole window.
wall=(windows[120][0]-windows[30][0])/90
fifo=(windows[120][1]-windows[30][1]+1)/90
draw=sum(n[1] for n in rows)/19200/90
cpu=sum(n[2] for n in rows)/19200/90
print(f'CPU {cpu:.3f}, wall {wall:.3f}, generous FIFO {fifo:.3f}, Draw {draw:.3f}, CPU outside both >= {cpu-draw-fifo:.3f} ms/frame; CPU-only remainder over 60Hz >= {cpu-draw-fifo-1000/60:.3f}')
