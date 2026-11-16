"""Difference device counters across exactly frames 31..120 of the wide opening."""
import re
import statistics
from pathlib import Path

paths = list(Path('build/switch-runtime/device-logs').glob('0.55.0-wide-*/boot.log'))
assert len(paths) == 1
s = paths[0].read_text()
def pair(expr):
    m = re.findall(expr, s)
    assert len(m) >= 2
    return [int(x) for x in m[:2]]
assert pair(r'3D scene flips=(\d+) ') == [30,120]
assert pair(r'\[CLOCK\] first=\d+ cpu_hz=(\d+)') == [1785000000]*2
assert pair(r'\[CLOCK\] first=\d+ cpu_hz=\d+ gpu_hz=(\d+)') == [307200000]*2
def delta(expr):
    a,b=pair(expr)
    assert b>=a
    return b-a
wall=delta(r'3D scene flips=\d+ draws=\d+ elapsed_ms=(\d+)')/90
wait=delta(r'render_work_ms=\d+ guest_wait_ms=(\d+)')/90
render=delta(r'3D scene render_work_ms=(\d+)')/90
gpu=delta(r'GPU command_buffers=\d+ gpu_us=(\d+) query_failures=0')/90000
assert delta(r'GPU command_buffers=(\d+)')==90
print(f'31..120: wall {wall:.3f}, excess {wall-1000/60:.3f}, render work {render:.3f}, guest render wait {wait:.3f}, GPU timestamp {gpu:.3f} ms/frame (overlapping).')
rows=re.findall(r'\[DRAW_BOUND\] frame=(\d+) draws=\d+ ticks=(\d+) cpu=(\d+) rc=0',s)
assert [int(f) for f,t,c in rows]==list(range(31,121))
draw,cpu=[statistics.mean(int(r[i]) for r in rows)/19200 for i in [1,2]]
print(f'Game CPU {cpu:.3f}, elapsed in Draw {draw:.3f}; even granting all Draw and render waiting for free, mean frame still {wall-wait-draw:.3f} ms assuming other work unchanged.')
