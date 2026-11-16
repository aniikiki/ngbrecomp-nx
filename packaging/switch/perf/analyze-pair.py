from pathlib import Path
from statistics import mean, median
import random, re, sys
p = Path(sys.argv[1])
rows = [tuple(map(int, m.groups())) for m in re.finditer('^\\[PAIR\\] (\\d+) (\\d+) (\\d+) (\\d+) (\\d+) (\\d+)$', p.read_text(), re.M)]
windows = [(1681, 120), (1801, 120)]
if any(row[0] <= 120 for row in rows):
    windows.insert(0, (33, 88))
for lo, length in windows:
    a = [x for x in rows if lo <= x[0] < lo + length]
    if [x[0] for x in a] != list(range(lo, lo + length)):
        sys.exit(f"Incomplete or unordered trial window starting at {lo}")
    pairs = [sorted(t, key=lambda x: x[1]) for t in zip(a[::2], a[1::2])]
    assert all((x[1] == 0 and y[1] == 1 for x, y in pairs))
    dif = [(x[2] - y[2]) / 1000000.0 for x, y in pairs]
    clusters = [mean(dif[i:i + 4]) for i in range(0, len(pairs), 4)]
    rng = random.Random(1234)
    boot = sorted((mean(rng.choices(clusters, k=len(clusters))) for _ in range(4000)))
    print(lo, 'base/alt ms %.3f %.3f; saved %.3f; 8-frame block bootstrap [%.3f, %.3f]; median pair %.3f' % (mean((x[2] for x, y in pairs)) / 1000000.0, mean((y[2] for x, y in pairs)) / 1000000.0, mean(dif), boot[99], boot[3899], median(dif)))
    for k in (3, 4, 5):
        print(' work', k, round(mean((x[k] for x, y in pairs)), 1), round(mean((y[k] for x, y in pairs)), 1))
