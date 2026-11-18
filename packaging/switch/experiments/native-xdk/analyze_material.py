"""Pair nearby ABBA frames with comparable geometry, without selecting on CPU time."""
import argparse
import csv
import json
from pathlib import Path
import random
import statistics as stats

parser = argparse.ArgumentParser()
parser.add_argument('directory', type=Path)
parser.add_argument('--mesh', action='store_true')
args = parser.parse_args()
path = args.directory
tables, headers = {}, {}
with (path / 'native-perf.csv').open() as file:
    for row in csv.reader(file):
        if not row:
            continue
        if row[0].startswith('#') and len(row[0]) == 2:
            headers[row[0][1:]] = row[1:]
        elif row[0] in headers:
            keys = headers[row[0]]
            assert len(row) == len(keys) + 1, row
            tables.setdefault(row[0], []).append(dict(zip(keys, map(int, row[1:]))))
native = {r['native_frame']: r for r in tables['N']}
render = {r['present']: r for r in tables['R']}
with (path / ('mesh.csv' if args.mesh else 'material.csv')).open() as file:
    materials = [{k: int(v) for k, v in row.items()} for row in csv.DictReader(file)]
with (path / 'frames.csv').open() as file:
    frames = [{k: int(v) for k, v in row.items()} for row in csv.DictReader(file)]
assert len(frames) == len(materials), (len(frames), len(materials))
selected = []
for material, frame in zip(materials, frames):
    f = material['native_frame']
    n = native.get(f)
    if not n or not material['attempts'] or frame['mission'] != 23 or frame['max_hp'] != 2400:
        continue
    # Lavapipe is GPU-bound in this replay. Compare thread CPU time, which
    # excludes sleeping in FrameWait; wall time/FPS cannot measure this change.
    if n['draws'] < 250 or n['profiled']:
        continue
    if any(render.get(i, {}).get('compile_us', 0) >= 1000 for i in (f-1, f)):
        continue
    assert 0 <= material['batches'] <= material['attempts'], material
    assert not material['batches'] or material['enabled'], material
    if material['enabled']:
        assert material['batches'] > 0, material
    selected.append({**n, **material, 'draws': n['draws'], 'block': (f-1)//32})

pairs = []
for block in sorted({r['block'] for r in selected}):
    a = [r for r in selected if r['block'] == block and not r['enabled']]
    b = [r for r in selected if r['block'] == block and r['enabled']]
    candidates = []
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            distance = abs(x['native_frame']-y['native_frame'])
            draws = abs(x['draws']-y['draws'])
            meshes = abs(x['attempts']-y['attempts'])
            if distance <= 16 and draws <= max(2, .01*max(x['draws'],y['draws'])) and meshes <= 2:
                candidates.append((draws + meshes + distance/32, i, j))
    used_a, used_b = set(), set()
    for _, i, j in sorted(candidates):
        if i in used_a or j in used_b:
            continue
        used_a.add(i); used_b.add(j)
        x, y = a[i], b[j]
        pairs.append({'block': block, 'a': x['native_frame'], 'b': y['native_frame'],
                      'before_ms': x['frame_cpu_us']/1000, 'after_ms': y['frame_cpu_us']/1000,
                      'draws_a': x['draws'], 'draws_b': y['draws'],
                      'meshes_a': x['attempts'], 'meshes_b': y['attempts'],
                      'state_calls_a': x['state_calls'], 'state_calls_b': y['state_calls']})
assert len(pairs) >= 30, f'Only {len(pairs)} matched pairs; insufficient evidence'
blocks = {}
for p in pairs:
    blocks.setdefault(p['block'], []).append(p['before_ms']-p['after_ms'])
grouped = list(blocks.values())
assert len(grouped) >= 8, f'Only {len(grouped)} independent blocks'
rng = random.Random(576)
bootstrap = []
for _ in range(5000):
    sample = [rng.choice(grouped) for _ in grouped]
    bootstrap.append(sum(map(sum, sample))/sum(map(len, sample)))
bootstrap.sort()
before = stats.mean(p['before_ms'] for p in pairs)
after = stats.mean(p['after_ms'] for p in pairs)
result = {'selected_frames': len(selected), 'pairs': len(pairs), 'blocks': len(grouped),
          'reference_cpu_ms': before, 'native_cpu_ms': after,
          'saved_ms': before-after, 'saved_percent': (before-after)/before*100,
          'saved_ms_block_bootstrap_95ci': [bootstrap[125], bootstrap[4874]],
          'reference_state_calls': stats.mean(p['state_calls_a'] for p in pairs),
          'native_state_calls': stats.mean(p['state_calls_b'] for p in pairs),
          'method': '8-frame ABBA, same 32-frame block, <=1% draw difference, <=2 mesh difference; bootstrap blocks, not individual frames',
          'scope': 'isolated ARM host replay; not a measurement of Switch FPS',
          'matched_frames': pairs}
(path / ('mesh-analysis.json' if args.mesh else 'material-analysis.json')).write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='matched_frames'}, indent=2))
