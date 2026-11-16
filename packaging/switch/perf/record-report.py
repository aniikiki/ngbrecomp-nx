"""Independent-scope timings; no nested measured clocks. Costs are host CPU only."""
import sys
from pathlib import Path
from statistics import mean
import random
p=Path(sys.argv[1])
data=p.read_text()
rows=[list(map(int,l.split()[1:])) for l in data.splitlines() if l.startswith('[RECORD_COST] ')]
opening='--opening' in sys.argv
window=range(1,121) if opening else range(1801,1921)
reason='verified 120 original demo frames' if opening else 'verified original combat window'
if [r[0] for r in rows]!=list(window) or any(len(r)!=23 for r in rows) or f'[RESULT] status=1 reason={reason}' not in data:
    raise SystemExit('Incomplete intact-draw replay')
def stat(xs,k):
    return sum(r[3+k] for r in xs)/sum(r[13+k] for r in xs)
scopes=('end-to-end Draw','state synchronization','SendState inclusive','resource headers','peek','fixed state','shader constants','lights, shader bindings and state command','draw packet / indices / submit','empty probe')
print('draws',sum(r[1] for r in rows),'sampled',sum(r[2] for r in rows),'clock control (ns)',round(stat(rows,9),1))
for k,label in enumerate(scopes[:-1]):
    def metric(xs):
        return (stat(xs,k)-stat(xs,9))*mean(r[1] for r in xs)/1e6
    rng=random.Random(177+k);groups=[rows[i:i+8] for i in range(0,len(rows),8)]
    boot=sorted(metric([r for g in rng.choices(groups,k=len(groups)) for r in g]) for _ in range(1000))
    print(f'{label}: {metric(rows):.3f} [{boot[24]:.3f}, {boot[974]:.3f}] ms/frame; n={sum(r[13+k] for r in rows)}')
