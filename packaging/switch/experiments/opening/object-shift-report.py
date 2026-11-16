"""Same-index, same-draw comparison across *all four* trials; report control drift separately."""
from pathlib import Path
from statistics import mean
import re
d=Path('build/switch-runtime/core-perf/opening-present-combined')
def log(arm):
    s=(d/f'object-shift-{arm}.log').read_text()
    assert '[RESULT] status=1 reason=verified 120 original demo frames' in s
    return s
checked=sorted(set(re.findall(r'\[SHIFT_CHECK\] bytes=(\d+)',log('verify'))))
assert checked
print('verified hit spans:',checked)
def read(arm):
    rows=re.findall(r'^\[PRESENT_MIX\] (\d+) (\d+) (\d+) (\d+) (\w+) (\d+) ',log(arm),re.M)
    assert len(rows)==120 and len({r[:2] for r in rows})==120
    return rows
a,b,c,e=map(read,['control-1','planned-1','planned-2','control-2'])
for label,low,high in [('whole',0,120),('late',31,119)]:
    rows=[tuple(int(r[5])/1e6 for r in group) for group in zip(a,b,c,e)
          if low<=int(group[0][1])<=high and len({r[:5] for r in group})==1]
    if not rows:
        print(label,'no identical intervals');continue
    m=list(map(mean,zip(*rows)))
    print(label,'four-way intervals',len(rows),'first/second saved ms',
          round(m[0]-m[1],4),round(m[3]-m[2],4),'control drift',round(m[3]-m[0],4))
