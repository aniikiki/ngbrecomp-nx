"""Check CPU clip-plane predictions against geometry from the unmodified draw."""
import argparse
from collections import Counter
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("log", type=Path)
args = p.parse_args()
counts = Counter()
frames = set()
done = False
for line in args.log.open():
    if line.startswith("[RESULT] status=1 reason=verified original combat window"):
        done = True
    if not line.startswith("[BOUND] "):
        continue
    frame, pred, samples, primitives = map(int, line.split()[1:])
    if pred not in range(5):
        raise SystemExit("unknown prediction")
    counts[pred] += 1
    frames.add(frame)
    if pred >= 2 and (samples or primitives):
        counts["unsafe"] += 1
        if counts["unsafe"] <= 3:
            print("prediction contradicted:", line.strip())
n = sum(counts[k] for k in range(5))
if not done or not n:
    raise SystemExit("no completed combat replay with matched GPU queries")
print(f"{n} sampled draws in {len(frames)} frames. Unsupported {counts[0]}; "
      f"retained {counts[1]}; side/near/far outside {counts[2]}/{counts[3]}/{counts[4]}.")
print(f"Certified outside: {sum(counts[k] for k in (2,3,4))/n:.2%}; "
      f"contradicted by GPU: {counts['unsafe']}")
if counts["unsafe"]:
    raise SystemExit(1)
