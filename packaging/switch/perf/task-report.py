"""Show the exclusive task share of each offline CPU-time window."""
import re
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text()
story = '--story' in sys.argv
for end, frames in (((1320,120), (1440,120)) if story else ((120, 90), (1800, 120), (1920, 120))):
    values = [(int(k, 16), int(ns)) for k, ns in
              re.findall(rf'^\[TASK\] end={end} key=([0-9a-f]+) ns=(\d+)$', text, re.M)]
    offline = re.search(rf'^\[OFFLINE\] end={end} .*?guest_ms=([\d.]+)', text, re.M)
    if story:
        windows = [(int(a),int(b),float(ms)) for a,b,ms in re.findall(
            r'^\[STORYCPU\] frames=(\d+)\.\.(\d+) guest_ms_per_frame=([\d.]+)', text, re.M)
            if end-frames < int(a) <= int(b) <= end]
        if [i for a,b,_ in windows for i in range(a,b+1)] != list(range(end-frames+1,end+1)):
            sys.exit(f'Incomplete story frame clock ending at {end}')
        outer = sum((b-a+1)*ms for a,b,ms in windows)
    elif offline:
        outer = float(offline[1])
    else:
        sys.exit(f'Missing frame clock ending at {end}')
    if not values:
        sys.exit(f'Missing task-clock window ending at {end}')
    total = sum(ns for _, ns in values)
    if abs(total / 1e6 - outer) > max(2, outer * 0.02):
        sys.exit(f'Task clock does not reconcile to frame clock at {end}')
    print(f'Frames {end-frames+1}-{end}: task clock {total/1e6:.2f} ms, frame clock {outer:.2f} ms')
    for key, ns in sorted(values, key=lambda it: -it[1])[:8]:
        tag = {0:'scheduler/unclassified', 1:'interrupt/DPC'}.get(key,
                f'child_{key & 0x7fffffff:08X}' if key >> 31 else f'task_{key:08X}')
        print(f'  {tag:<24} {ns/frames/1e6:6.3f} ms/frame  {100*ns/total:5.1f}%')
