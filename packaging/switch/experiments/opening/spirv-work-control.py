"""Compare two cache-table pairs and two game-code pairs at the same Present ordinals."""
from pathlib import Path
from statistics import mean

logs = Path('build/switch-runtime/core-perf/opening-present-combined')
def read(stem):
    s = (logs / (stem + '.log')).read_text()
    assert 'reason=verified 120 original demo frames' in s
    assert s.index('[PRESENT_MIX]') > s.index('[WIDE] moving Vulkan scanouts=')
    rows = [l.split()[1:] for l in s.splitlines() if l.startswith('[PRESENT_MIX] ')]
    assert len(rows) == 120 and all(len(r) == 8 for r in rows)
    return [(r[:5], *map(int, r[5:])) for r in rows]

runs = [read(p+'-'+arm) for p,arms in [
    ('openingspirv', ['old-1','complete-1','old-2','complete-2']),
    ('jointbuf', ['base-1','next-1','base-2','next-2'])] for arm in arms]
pairs = [(0,1),(2,3),(4,5),(6,7)]
for lo,hi in [(1,30),(31,120)]:
    same = [i for i,r in enumerate(runs[0]) if lo <= int(r[0][1]) < hi
            and int(r[0][1]) == 1+int(r[0][0])
            and all(a[i][0] == r[0] for a in runs)]
    for tol in (None, .025, .01):
        # Test work similarity *within* each A/B; do not match on CPU time.
        cohort = [i for i in same if tol is None or all(
            abs(runs[a][i][k]-runs[b][i][k]) <= tol*max(1,runs[a][i][k])
            for a,b in pairs for k in (2,3))]
        print(lo,hi,'work tolerance',tol,'n',len(cohort))
        if cohort:
            for a,b in pairs:
                diffs = [mean(runs[a][i][k]-runs[b][i][k] for i in cohort) for k in (1,2,3)]
                print('  ',a,b,'old minus new: ms, entries, polls',
                      round(diffs[0]/1e6,4),round(diffs[1]),round(diffs[2]))
