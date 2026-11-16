"""Same-frame bound: synchronous submit CPU cannot exceed elapsed time inside Draw."""
from pathlib import Path
import re,sys,statistics
s=Path(sys.argv[1]).read_text()
rows=[tuple(map(int,m)) for m in re.findall(r'\[DRAW_BOUND\] frame=(\d+) draws=(\d+) ticks=(\d+) cpu=(\d+) rc=(\d+)',s)]
if [r[0] for r in rows]!=list(range(31,121)) or not all(n and wall and cpu and not rc for _,n,wall,cpu,rc in rows):
    sys.exit('Expected exactly one complete opening, valid thread clock and draws on every frame')
hz=int(re.search(r'\[CALLERS\] thread=guest .*?tick_hz=(\d+)',s)[1]) if 'tick_hz=' in s else 19200000
ms=lambda i:statistics.mean(r[i] for r in rows)*1000/hz
print('31..120: CPU %.3f ms/frame; Draw elapsed %.3f ms/frame; CPU outside Draw >= %.3f ms/frame'%(ms(3),ms(2),ms(3)-ms(2)))
