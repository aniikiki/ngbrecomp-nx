"""Same-frame excess over 60 Hz after generously crediting all synchronous Draw elapsed time."""
import re, statistics as st, sys
from pathlib import Path
s=Path(sys.argv[1]).read_text()
rows=[tuple(map(int,m)) for m in re.findall(r'\[DRAW_BOUND\] frame=(\d+) draws=(\d+) ticks=(\d+) cpu=(\d+) rc=(\d+)',s)]
assert [r[0] for r in rows]==list(range(31,121)) and all(n and t and c and not rc for _,n,t,c,rc in rows)
hz=int(re.search(r'tick_hz=(\d+)',s)[1]) if 'tick_hz=' in s else 19200000
for start,end in [(31,60),(61,90),(91,120),(31,120)]:
    part=[r for r in rows if start<=r[0]<=end]
    floor=[(c-t)*1000/hz for _,_,t,c,_ in part]
    draws=[r[1] for r in part]
    print(f'{start}..{end}: mean Draw calls {st.mean(draws):.1f}, mean CPU outside Draw >= {st.mean(floor):.3f} ms, over budget even without Draw {sum(x>1000/60 for x in floor)}/{len(part)}')
