"""Match exclusive mesh/index timers to the same handheld thread-CPU samples."""
import re
import sys
from pathlib import Path

log = Path(sys.argv[1]).read_text()
blocks = re.split(r'^\[SERVICE\] 3D scene window frames=', log, flags=re.M)[1:3]
snapshots = []
for block, length, end in zip(blocks, (30, 90), (30, 120)):
    assert int(block.split()[0]) == length
    assert int(re.search(r'3D scene flips=(\d+)', block)[1]) == end
    snapshots.append(tuple(map(int, re.search(
        r'sampled_frames=(\d+) indexed_us=(\d+) mesh_excluding_index_us=(\d+) remaining_us=(\d+)',
        block).groups())))
n, indexed, mesh, remaining = (b-a for a, b in zip(*snapshots))
rows = re.findall(r'\[DRAW_BOUND\] frame=(\d+) draws=\d+ ticks=\d+ cpu=(\d+) rc=(\d+)', log)
assert [int(f) for f, _, rc in rows if rc == '0'] == list(range(31, 121)) and len(rows) == 90
sample = [(int(f), int(cpu)) for f, cpu, _ in rows
          if (int(f)-1) % 16 == 9*((int(f)-1)//16) % 16]
assert len(sample) == n and min(indexed, mesh, remaining) >= 0
cpu = sum(t for _, t in sample) / (19200*n)
indexed, mesh, remaining = (v / (1000*n) for v in (indexed, mesh, remaining))
budget = 1000/60
print('frames:', [f for f, _ in sample])
print(f'CPU {cpu:.4f}; elapsed index {indexed:.4f}, exclusive mesh {mesh:.4f}, other {remaining:.4f} ms')
for name, elapsed in [('index', indexed), ('exclusive mesh', mesh), ('both', mesh+indexed)]:
    print(f'{name}: optimistic CPU after removal {cpu-elapsed:.4f} ms; '
          f'required share of elapsed to save {(cpu-budget)/elapsed:.1%}')
