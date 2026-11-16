"""Timing comparisons for the actual ARM flag specialization against its unmodified unit."""
from pathlib import Path
from statistics import mean
import re
d=Path('build/switch-runtime/core-perf/opening-present-combined')
def read(arm,i):
    s=(d/f'{prefix}-{arm}-{i}.log').read_text()
    assert 'verified 120 original demo frames' in s
    rows=[(int(end), (n,v,h), int(ns)) for end,n,v,h,ns in re.findall(r'^\[PRESENT_MIX\] \d+ (\d+) (\d+) (\d+) (\w+) (\d+) ',s,re.M)]
    assert len(rows)==120
    wall=int(re.search(r'3D scene flips=120 draws=\d+ elapsed_ms=(\d+)',s)[1])
    return rows,wall
import sys
pixel='--pixel-plan' in sys.argv
four='--four-piece' in sys.argv
ps='--ps-range' in sys.argv
if ps:
    verification=(d/'ps-range-verify.log').read_text()
    assert 'verified 120 original demo frames' in verification
    checked={}
    for slot in [0,2,3,5]:
        marks=list(map(int,re.findall(r'^\[PS_RANGE_CHECK\] '+str(slot)+r' (\d+)$',verification,re.M)))
        assert marks and marks==list(range(4096,marks[-1]+1,4096))
        checked[slot]=marks[-1]
    print('real full-range checks at least',checked)
shift='--object-shift' in sys.argv
prefix='object-shift' if shift else 'ps-range' if ps else 'four-piece' if four else 'pixel-plan' if pixel else 'ordered'
if four:
    verification=(d/'four-piece-verify.log').read_text()
    assert 'verified 120 original demo frames' in verification
    marks=list(map(int,re.findall(r'^\[FOUR_PIECE\] (\d+)$',verification,re.M)))
    assert marks and marks==list(range(65536,marks[-1]+1,65536))
    print('real 256-byte masks checked at least',marks[-1])
if pixel:
    verification=(d/'pixel-plan-verify.log').read_text()
    assert 'verified 120 original demo frames' in verification
    marks=list(map(int,re.findall(r'^\[PIXEL_PLAN_CHECK\] (\d+)$',verification,re.M)))
    assert marks==list(range(4096,marks[-1]+1,4096))
    print('real register-state checks at least',marks[-1])
for i in (1,2):
    (a,w),(b,v)=(read(arm,i) for arm in (('control','planned') if (pixel or four or ps or shift) else ('ordered-control','ordered-branch')))
    late=[(x[2]-y[2])/1e6 for x,y in zip(a,b) if x[1]==y[1] and 31<=x[0]<120 and 31<=y[0]<120]
    print(i,'full wall',w,v,'cpu ms/frame',*(round(mean(x[2] for x in arm)/1e6,4) for arm in (a,b)),'matching geometry',sum(x[1]==y[1] for x,y in zip(a,b)),'matched late',len(late),'cpu saved',round(mean(late),4) if late else None)
