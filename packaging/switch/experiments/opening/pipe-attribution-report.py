"""Measure unions and critical-path overlap, never add parallel worker times."""
from pathlib import Path
import re,sys
s=Path(sys.argv[1]).read_text()
assert re.search(r'\[BOOT\] NGB Switch startup adapter 0\.55\.7-pipe2?;',s)
rows=[tuple(map(int,r.split())) for r in re.findall(r'\[PIPE_ATTR\] ([0-9 ]+)',s)]
assert [r[0] for r in rows]==list(range(1,121))
m=re.search(r'\[PIPE_ATTR_END\] tables=(\d+) bad=0 hz=(\d+)',s)
assert m and int(m[1])>0 and int(m[2])>0
assert all(len(r)==7 and 0<=r[-1]<=min(r[-2],r[-3]) for r in rows)
for lo,hi in [(1,1),(2,2),(3,30),(31,60),(1,60),(31,120)]:
    a=rows[lo-1:hi]
    print(lo,hi,'create starts/ends',sum(x[1] for x in a),sum(x[2] for x in a),
          'wait / creation / overlap ms',*[round(sum(x[k] for x in a)*1000/int(m[2]),3) for k in (4,5,6)])
