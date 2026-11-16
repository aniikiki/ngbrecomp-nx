"""Compare seeded ABBA opening runs without full-frame readback."""
from pathlib import Path
import re
from statistics import mean

root = Path('build/switch-runtime/core-perf/opening-present-combined')
def read(name):
    log = (root / f'strip-time-{name}.log').read_text()
    assert 'reason=verified 120 original demo frames' in log, name
    wall = [int(re.search(rf'3D scene flips={n} draws=\d+ elapsed_ms=(\d+)', log)[1]) for n in (30,120)]
    rows = [(int(b), (n,v,h), int(ns)) for b,n,v,h,ns in re.findall(r'^\[PRESENT_MIX\] \d+ (\d+) (\d+) (\d+) (\w+) (\d+) ',log,re.M)]
    assert len(rows) == 120
    submitted = int(re.findall(r'3D scene Direct3D draws=\d+ submitted=(\d+) scanouts=119 ', log)[-1]); merged = int(re.findall(r' strips_merged=(\d+)',log)[-1]); print(name,'wall30/120',wall,'submitted',submitted,'merged',merged,'CPU ms/frame',round(mean(r[2] for r in rows)/1e6,3)); return rows,wall

for i in (1,2):
    a,w = read(f'control-{i}'); b,v = read(f'joined-{i}')
    late = [(x[2]-y[2])/1e6 for x,y in zip(a,b) if x[1]==y[1] and 31<=x[0]<120 and 31<=y[0]<120]
    print('paired',i,'matched late',len(late),'CPU ms/frame saved',round(mean(late),4) if late else None,'wall ms/frame saved',round((w[1]-v[1])/120,4))
