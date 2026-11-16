"""Net sampled device-status time; no conversion to device milliseconds."""
from pathlib import Path
import re
f=Path('build/switch-runtime/core-perf/opening-irq-cost/distribution.log')
s=f.read_text()
assert '[RESULT] status=1 reason=verified 120 original demo frames' in s
rows=[list(map(int,l.split())) for l in re.findall(r'^\[IRQ_COST\] (.+)$',s,re.M)]
assert [(r[0],r[1]) for r in rows]==[(n,j) for n in (30,120) for j in range(4)]
for end,n in ((30,30),(120,90)):
 print('frames',end-n+1,'to',end)
 for _,j,total,samp,elapsed,empty,hit,t_hit,signaled in (r for r in rows if r[0]==end):
    assert 0<=hit<=samp<=total and hit<=signaled<=total
    if not samp:
        print(j,'no timed sample:',total,'calls');continue
    print(('OHCI','APU','AC97','NV2A')[j],
          f'{total/n:.0f} calls/frame; {signaled/total:.2%} nonzero; {samp} timed;',
          f'{elapsed/samp:.1f} gross, {empty/samp:.1f} paired-clock ns/call;',
          f'{(elapsed-empty)/samp*total/n/1e6:.4f} estimated host ms/frame')
