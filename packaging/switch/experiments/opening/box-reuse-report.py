"""Report opportunity counts only for verified original opening windows."""
from pathlib import Path
import re
import sys

log = Path(sys.argv[1]).read_text(errors='replace')
if '[RESULT] status=1 reason=verified 120 original demo frames' not in log:
    raise SystemExit('incomplete opening replay')
rows = re.findall(r'^\[BOX_REUSE\] (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)$', log, re.M)
if [r[0] for r in rows] != ['30', '120']:
    raise SystemExit('missing or duplicated windows')
for frame, total, eligible, address, shape, exact in (map(int, r) for r in rows):
    assert 0 <= exact <= shape <= address <= eligible <= total
    print(f'end={frame} total={total} eligible={eligible} excluded={total-eligible}'
          f' same_address={address} same_shape={shape} exact={exact}'
          f' exact/eligible={exact/eligible:.2%}' if eligible else f'end={frame}: no eligible queries')
