"""Combine the preregistered original and reverse-order reruns, including outliers."""
from pathlib import Path
from statistics import mean, median
import re

root = Path("build/switch-runtime/core-perf/wide-start")
def frames(name):
    s = (root / (name + ".log")).read_text()
    if "[RESULT] status=1 reason=verified 120 original demo frames" not in s:
        raise SystemExit("Incomplete: " + name)
    rows = [tuple(map(int, m)) for m in re.findall(
        r"^\[OPEN_PAIR\] (\d+) \d+ (\d+) (\d+)$", s, re.M)]
    assert [r[0] for r in rows] == list(range(1, 121)), name
    return rows

pairs = [(frames(f"full-page-original-{i}"), frames(f"full-page-limit-{i}"))
         for i in range(1, 5)]
pairs.extend((frames(f"full-page-retest-original-{i}"), frames(f"full-page-retest-full-page-{i}"))
             for i in (1, 2))
for start, end in [(0, 30), (30, 120), (0, 120)]:
    saved, draw = [], []
    for a, b in pairs:
        aa, bb = a[start:end], b[start:end]
        saved.append(100 * (1 - sum(r[1] for r in bb) / sum(r[1] for r in aa)))
        draw.append(sum(r[2] for r in bb) / sum(r[2] for r in aa))
    print(f"frames {start+1}-{end}: host CPU saved (%)", *(round(x, 2) for x in saved),
          f"mean={mean(saved):.2f} median={median(saved):.2f}",
          "draw ratios", *(round(x, 3) for x in draw))
