"""Separate title thread elapsed time from matched game thread CPU in the opening."""
from pathlib import Path
import re,sys
from statistics import mean
d=Path('build/switch-runtime/core-perf/opening-present-combined')
def load(arm):
    s=(d/f'openingspirv-{arm}.log').read_text()
    assert 'reason=verified 120 original demo frames' in s
    def unique(expr):
        values=re.findall(expr,s);assert len(values)==1;return int(values[0])
    assert '[IDLE_DEVICE] adopted at scene start' in s
    if arm not in ('fill','check'):
        assert s.index('[PRESENT_MIX]')>s.index('[WIDE] moving Vulkan scanouts=')
    work=unique(r'\[IDLE_WORKER\] ready=1 work_ns=(\d+)')/1e6
    join=unique(r'\[IDLE_WORKER\] join_ns=(\d+)')/1e6
    rows=[line.split()[1:] for line in s.splitlines() if line.startswith('[PRESENT_MIX] ')]
    assert len(rows)==120 and all(len(r)==8 for r in rows)
    assert '118 shaders and 167 pipelines made ahead' in s
    expected=93 if arm.startswith(('old','fill')) else 98
    assert f'loaded {expected} packaged shaders' in s
    return work,join,rows
groups=[('fill','check')] if '--initial' in sys.argv else [('old-1','complete-1'),('old-2','complete-2')]
runs=[(load(a),load(b)) for a,b in groups]
matching=[i for i in range(120) if all(r[2][i][:5]==runs[0][0][2][i][:5] for pair in runs for r in pair)]
for a,b in runs:
    print('title worker / join elapsed ms old -> complete',a[:2],b[:2])
    for lo,hi in ((1,30),(31,120)):
        cohort=[i for i in matching if lo<=int(a[2][i][1])<hi and int(a[2][i][0])+1==int(a[2][i][1])]
        assert cohort, 'no shared matched interval'
        print(lo,hi,'matched',len(cohort),'game thread CPU saving ms (old - complete)',
                         round(mean((int(a[2][i][5])-int(b[2][i][5]))/1e6 for i in cohort),4))
