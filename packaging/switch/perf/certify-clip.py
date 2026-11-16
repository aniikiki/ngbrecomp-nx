"""Fail on any release-positive mesh producing a clipped primitive or sample.
Only for the --certify replay, which runs precisely that subset of draws."""
import sys
from pathlib import Path

log=Path(sys.argv[1]).read_text()
rows=[l.split() for l in log.splitlines() if l.startswith('[CLIP] ')]
if not rows or '[RESULT] status=1 reason=verified original combat window' not in log:
    raise SystemExit("no completed combat oracle")
if not any('[BOOT]' in l and 'rigid clip' in l for l in log.splitlines()):
    raise SystemExit("not the packaged game core")
if not any(l.startswith('[CERTIFY]') for l in log.splitlines()):
    # Earlier host runners did not emit a banner. Require their generated
    # source explicitly; never use an ordinary one-in-seven coverage log.
    if len(sys.argv)!=3: raise SystemExit("supply the exact old oracle backend.cpp")
    src=Path(sys.argv[2]).read_text()
    assert 'if(f>=1800 && f<1916 && predicted_out && coverage_[slot_].size()>=kVisQueries)std::abort()' in src
    assert '++rigid_skipped_;predicted_out=true;' in src and '(++coverage_seq_%7)' not in src
bad=[r for r in rows if any(int(r[k]) for k in (3,7,8))]
if bad: raise SystemExit(f"{len(bad)} contradicted draws; first: {bad[0]}")
print(f"{len(rows)} production-positive draws across {len(set(r[1] for r in rows))} concurrent scene frames: zero output primitives, fragments and samples")
