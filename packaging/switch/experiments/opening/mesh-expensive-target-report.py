from pathlib import Path
import re
s=Path('build/switch-runtime/core-perf/opening-mesh-expensive-target/budget.log').read_text()
assert 'verified 120 original demo frames' in s
for frame,frames in ((30,30),(120,90)):
    rows=[tuple(map(int,m)) for m in re.findall(r'^\[TREE_COST\] '+str(frame)+r' (\d+) calls=(\d+) samples=(\d+) ns=(\d+) blanks=(\d+) blank_ns=(\d+) cross=(\d+)$',s,re.M)]
    assert len(rows)==18 and sum(m[1] for m in rows)>0
    assert all(not any(row[1:]) for row in rows[4:]) and all(row[3] and row[2] and row[4] for row in rows[:3])
    for i,c,n,t,b,z,x in rows:
        if c:print(frame,('1D7810','1D7800','1D7100','other')[i],c,'samples',n,'blanks',b,'us/frame',round((t/n-z/b)*c/frames/1000,2) if n and b and not x else None)
