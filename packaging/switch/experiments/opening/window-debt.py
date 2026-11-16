"""Keep cold frames visible: absolute CPU saved per phase and rank of largest contributor."""
from pathlib import Path
import re,sys,statistics as st
d=Path('build/switch-runtime/core-perf/wide-start')
def frames(tag,arm,i):
    s=(d/f'{tag}-{arm}-{i}.log').read_text()
    assert '[RESULT] status=1 reason=verified 120 original demo frames' in s
    rows=[tuple(map(int,m)) for m in re.findall(r'^\[OPEN_PAIR\] (\d+) \d+ (\d+) (\d+)$',s,re.M)]
    assert [f for f,*_ in rows]==list(range(1,121))
    return rows
for tag in sys.argv[1:]:
    pairs=[(frames(tag,'original',i),frames(tag,'limit',i)) for i in range(1,5)]
    for start,end in [(1,2),(3,30),(31,60),(61,90),(91,120),(1,120)]:
        results=[]
        for a,b in pairs:
            aa,bb=a[start-1:end],b[start-1:end]
            savings=[(x[1]-y[1])/1e6 for x,y in zip(aa,bb)]
            results.append((sum(savings), st.median(savings),sum(x[2]-y[2] for x,y in zip(aa,bb))))
        print(tag,f'{start}..{end}', 'paired total CPU ms saved',*[round(x[0],2) for x in results], 'median frame saving ms',round(st.mean(x[1] for x in results),3),'mean draw difference',round(st.mean(x[2] for x in results),1))
