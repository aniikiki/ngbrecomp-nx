"""Recover the recorder budget from the original first two hardware reports."""
import re
import sys
from pathlib import Path

log = Path(sys.argv[1]).read_text()
# Limit to the first attract session and use its cumulative totals once.
end = re.search(r'^\[SERVICE\] 3D scene flips=120 draws=\d+ elapsed_ms=\d+$', log, re.M)
if not end:
    raise SystemExit('missing opening endpoint')
chunks = re.split(r'^\[SERVICE\] 3D scene window frames=', log[:end.end()], flags=re.M)[1:]
if [c.split()[0] for c in chunks] != ['30', '90']:
    raise SystemExit('unexpected windows before frame 120')
last = chunks[-1]
def fields(pattern):
    found = re.findall(pattern, last)
    if len(found) != 1:
        raise ValueError(pattern)
    return tuple(map(int, found[0]))
sync, record = fields(r'sampled guest sync_us=(\d+) record_us=(\d+)')
(n,) = (int(re.search(r'sampled_frames=(\d+)', last)[1]),)
cmds, gpu = fields(r'GPU command_buffers=(\d+) gpu_us=(\d+) query_failures=0')
draws, adjacent, candidates = (int(re.search(k + r'=(\d+)', last)[1]) for k in
                               ('Direct3D draws', 'adjacent_same_state','list_candidates'))
print(f'{n} sampled frames: sync {sync/n/1000:.3f}, record {record/n/1000:.3f} ms/frame (elapsed inside Draw)')
print(f'{cmds} command buffers: GPU {gpu/cmds/1000:.3f} ms/buffer')
print(f'{draws} Direct3D draws, {adjacent} adjacent with unchanged state, {candidates} list candidates')
