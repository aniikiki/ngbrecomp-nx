"""Report sampled wall time, without attributing waits to CPU execution."""
import re
import sys
from pathlib import Path

labels = "入口 状态同步 记录器入口 资源头 peek 固定状态 常量灯光等 索引与相邻检查 入队批提交 XDK返回".split()
pattern = re.compile(r"\[INDEX_LEDGER\]\s+((?:\d+\s+){17})cal1024=(\d+)")
rows = pattern.findall(Path(sys.argv[1]).read_text(errors="replace"))
if len(rows) != 2:
    sys.exit("Expected one complete opening (two ledger rows). Select one run from the log.")
for (data, cal), (end, frames) in zip(rows, [(30, 30), (120, 90)]):
    f, hz, calls, sampled, nested, cross, total, *parts = map(int, data.split())
    if f != end or not (hz and total and calls >= sampled > 0) or nested or cross or sum(parts) != total:
        sys.exit(f"Invalid or incomplete sample: frame {f}")
    scale = 1000 / hz * calls / sampled / frames
    print(f"frames {end-frames+1}..{end}, samples {sampled}/{calls}, estimated elapsed {total*scale:.3f} ms/frame, clock pair {int(cal)/1024/hz*1e6:.3f} us")
    for label, ticks in sorted(zip(labels, parts), key=lambda x: -x[1]):
        print(f"{label}: {ticks/total:.1%}, estimated {ticks*scale:.3f} ms/frame")
