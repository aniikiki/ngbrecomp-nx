"""Require the branch and moving scanouts before comparing both orders."""
from pathlib import Path
import re
base=Path('build/switch-runtime/core-perf/opening-present-combined')
def get(arm):
    s=(base/f'blend-palette-{arm}.log').read_text()
    assert 'reason=verified 120 original demo frames' in s
    assert re.findall(r'^\[PALETTE\] mode1 control=(\d+)$',s,re.M)==[str(int(arm.startswith('control')))]
    moving,=map(int,re.findall(r'^\[WIDE\] moving Vulkan scanouts=(\d+)$',s,re.M))
    assert moving>=8
    windows=re.findall(r'3D scene flips=(30|120) draws=(\d+) elapsed_ms=(\d+)',s)
    assert [int(f) for f,d,t in windows]==[30,120]
    return windows,moving
for i in (1,2):
    a,ma=get(f'control-{i}');b,mb=get(f'planned-{i}')
    print('pair',i,'moving',ma,mb)
    for (f,d,t),(g,e,u) in zip(a,b):
        print(f,'draws',d,e,'wall ms old -> candidate',t,u)
