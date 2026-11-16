"""Count mutually exclusive visible stacks; no conversion to CPU time."""
from pathlib import Path
from collections import Counter
import json, re, runpy

base = Path("build/switch-runtime")
h = base / "history/0.51.0-rc1"
api = runpy.run_path("packaging/switch/analyze-profile.py")
sym = api["load_symbols"](h / "symbols.gz")
log = base / json.loads((h / "deployment.json").read_text())["hardware_log"]
samples = api["parse_windows"](log.read_text().splitlines())[1, 120]["profiles"]["guest"][1]
for start, end in [(1, 30), (31, 120)]:
    counts, outcomes, callers = Counter(), Counter(), Counter()
    for frame, _, _, _, _, pcs in samples:
        if not start <= frame <= end:
            continue
        counts["all"] += 1
        labels = [sym(pc) for pc in pcs]
        ids = [m.group(1) if (m := re.search(r"(?:sub|orig)_([A-F0-9]{8})(?:\b|_)", s)) else "" for s in labels]
        if "003C6100" in ids:
            counts["viewport wrapper"] += 1
            callers[next((x for x in ids[ids.index("003C6100")+1:] if x and x != "003C6100"), "unknown")] += 1
        if not {"001D6E20", "001D7100"}.issubset(ids):
            continue
        counts["material chain"] += 1
        if "003C8930" in ids:
            if "003C6100" in ids:
                outcome = "VS guest viewport"
            elif any("Before" in s for s in labels):
                outcome = "VS hook"
            else:
                outcome = "VS other"
        else:
            outcome = next((x for x in ids if x.startswith("003C")), "other")
        outcomes[outcome] += 1
    print(start, end, dict(counts), dict(outcomes), dict(callers))
