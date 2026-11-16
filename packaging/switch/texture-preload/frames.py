"""Report full flip intervals separately from render-thread texture work."""
from pathlib import Path
import re,sys,statistics
p=Path(sys.argv[1])
for n in sys.argv[2:] or ('wide-off','wide-on'):
    s=(p/(n+'.log')).read_text()
    assert '[RESULT] status=1 reason=verified 120 original demo frames' in s
    assert '2_VI_WIDE_B.sfd' in s and '118 shaders and 167 pipelines made ahead' in s
    rows=[(int(i),int(t)/1e6) for i,t in re.findall(r'^\[TEX_FLIP\] (\d+) (\d+)$',s,re.M)]
    assert [i for i,_ in rows]==list(range(1,121))
    ts=[t for i,t in rows]
    print(n, 'first/second, first 2 sum, first 30 sum, full 120 sum (ms):',
          *(round(x,2) for x in (ts[0],ts[1],sum(ts[:2]),sum(ts[:30]),sum(ts))))
    print('worst frame:',max(rows,key=lambda x:x[1]),'p95 ms:', round(sorted(ts)[113],2))
