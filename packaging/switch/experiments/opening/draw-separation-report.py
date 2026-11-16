"""Report adjacent recorder draws before emission; compatibility masks are necessary, not sufficient."""
from pathlib import Path
import re
s=Path('build/switch-runtime/core-perf/opening-draw-separation/budget.log').read_text()
assert 'reason=verified 120 original demo frames' in s
for f in (30,120):
    rows={int(k):(int(a),int(b)) for k,a,b in re.findall(r'^\[DRAW_SEP\] '+str(f)+r' (\d+) (\d+) (\d+)$',s,re.M)}
    assert rows and 256 in rows and rows[256][1]==0
    print(f,'draws',sum(sum(v) for v in rows.values()),'first/after barrier',rows[256][0])
    pairs={k:b for k,(a,b) in rows.items() if k<256 and b}
    print('adjacent indexed same primitive',sum(pairs.values()),'no reported change',pairs.get(0,0),
          'only vertex constants/streams (incl unchanged)',sum(n for k,n in pairs.items() if not k&~3))
    print('inclusive changed categories',[(name,sum(n for k,n in pairs.items() if k&bit)) for name,bit in
        zip('vsc stream/index texture/palette transform other-state header peek shader'.split(),(1,2,4,8,16,32,64,128))])
    print('top disjoint reasons',sorted(pairs.items(), key=lambda x:-x[1])[:10])
