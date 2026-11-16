"""Partition delivered game-thread CPU samples by exact owner outside nested D3D calls."""
import re
from bisect import bisect_right
from collections import Counter
from pathlib import Path

root = Path("build/switch-runtime/core-perf")
guests = []
for dirname in ("opening-xdk-pc-scope", "opening-outside-operand"):
    d = root / dirname
    symbols = sorted((int(a, 16), int(n, 16), name) for a, n, _, name in
                     (row.split(maxsplit=3) for row in (d/"symbols.txt").read_text().splitlines()))
    starts = [s[0] for s in symbols]
    counts = [Counter(), Counter()]
    guest = Counter()
    for run in range(1, 5):
        log = (d/f"run-{run}.log").read_text()
        assert "verified 120 original demo frames" in log
        modules = {(int(f), int(pc, 16)): (Path(path).name, sym) for f, pc, path, sym in
                   re.findall(r"^\[FRAME_MODULE\] (\d+) (\w+) \w+ (\S+) (\S+)$", log, re.M)}
        for f, depth, pc in re.findall(r"^\[D3D_SCOPE_PC\] (\d+) (\d+) (\w+)$", log, re.M):
            f, pc = int(f), int(pc, 16)
            if int(depth) or not 1 <= f <= 120: continue
            mod, sym = modules.get((f,pc), ("unknown","?"))
            if mod == "replay":
                i = bisect_right(starts, pc)-1
                sym = symbols[i][2] if i >= 0 and pc < starts[i]+symbols[i][1] else "unresolved ELF"
                if re.match(r"^(?:ngb_reg_)?(?:sub_|d3d_orig_)[0-9A-F]+", sym):
                    if f > 30: guest[re.sub(r"^ngb_reg_", "", sym).split(".localalias")[0]] += 1
                    sym = "guest"
            else: sym = mod + ":" + sym
            counts[f>30][sym] += 1
    guests.append(guest)
    for stage, c in zip(("1-30","31-120"), counts):
        print(dirname,stage,sum(c.values()),c.most_common(20))

discovery, holdout = guests
for limit in (5, 10, 20, 50):
    names = [name for name, _ in discovery.most_common(limit)]
    print("discovery top", limit, "hits in discovery/holdout",
          sum(discovery[n] for n in names), sum(holdout[n] for n in names),
          "of", sum(discovery.values()), sum(holdout.values()))
print("top 10 (discovery, holdout):", [(n, v, holdout[n]) for n,v in discovery.most_common(10)])
