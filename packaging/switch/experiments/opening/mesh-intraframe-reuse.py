"""Count repeated producer inputs within a flip; equality never suppresses a draw."""
from collections import Counter
from pathlib import Path
from struct import Struct

for tag in ('join', 'early'):
    folder = Path('build/switch-runtime/core-perf/opening-clip-' + tag)
    log = (folder / 'joined.log').read_text()
    assert '[JOIN] original opening motion verified at 120' in log and 'reason=finished joined opening' in log
    draw_stage = {}
    for seq, stage, *_ in Struct('<2I192s16f6f').iter_unpack((folder / 'draw.bin').read_bytes()):
        assert seq not in draw_stage
        draw_stage[seq] = stage
    frame = seq = 0
    counts = [Counter(), Counter()]
    for idx, f, part, pc, n, ns, matrices in Struct('<6I192s').iter_unpack((folder / 'producer.bin').read_bytes()):
        assert idx == seq + 1 and f in (frame, frame+1) and 1 <= f <= 120 and n in (0, 1)
        if f != frame:
            seen = {}
            prev = None
            frame = f
        seq = idx
        c = counts[f > 30]
        c['all'] += 1
        assert (idx in draw_stage) == bool(n)
        identity = pc, part
        key = identity, matrices
        if identity in seen:
            c['same_part'] += 1
        if key in seen:
            c['full'] += 1
            c['full_ns'] += ns
            c['consecutive'] += prev == key
            c['both_draw'] += n and seen[key][0]
            if n and seen[key][0]:
                c['different_cull'] += bool(draw_stage[idx]&2) != bool(seen[key][1]&2)
        seen[identity] = True
        seen[key] = n, draw_stage.pop(idx, 0)
        prev = key
    assert frame == 120 and not draw_stage
    for frames, c in zip((30, 90), counts):
        print(tag, frames, dict(c), 'inclusive repeated ms/frame', round(c['full_ns']/frames/1e6, 4))
