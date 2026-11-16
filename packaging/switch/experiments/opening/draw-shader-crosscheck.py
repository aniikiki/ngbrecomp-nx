from pathlib import Path
import re
d=Path('build/switch-runtime/core-perf')
for variant in ('detail','reuse'):
    s=(d/f'opening-draw-shader-{variant}/budget.log').read_text()
    assert 'verified 120 original demo frames' in s
    strips=[int(n) for n in re.findall(r'\bstrips_merged=(\d+)',s)]
    actual=[tuple(map(int,m)) for m in re.findall(r'adjacent_same_state=(\d+) list_candidates=(\d+)',s)]
    assert len(strips)>=2 and len(actual)>=2
    for i,f in enumerate((30,120)):
        masks={int(k):int(b) for k,a,b in re.findall(r'^\[DRAW_SEP\] '+str(f)+r' (\d+) (\d+) (\d+)$',s,re.M)}
        detail={int(k):int(c) for k,c in re.findall(r'^\[DRAW_SHADER\] '+str(f)+r' (\d+) (\d+)$',s,re.M)}
        assert sum(detail.values())==masks.get(128,0)
        print(variant,f,'indexed pairs',sum(masks.values()),'no recorded change',masks.get(0,0),
              'only shader change:',detail,'recorder within batch (same state / eligible lists)',[n-(actual[i-1][j] if i else 0) for j,n in enumerate(actual[i])],'actual joined strips',strips[i]-(strips[i-1] if i else 0))
