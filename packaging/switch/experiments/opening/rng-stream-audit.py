"""Independent return-value oracle for the fixed-seed CRT, not a scene simulator."""
from pathlib import Path
import re
d=Path('build/switch-runtime/core-perf/opening-rng-correspondence')
mask=(1<<64)-1
def digest(xs):
    h=14695981039346656037
    for x in xs:h=((h^x)*1099511628211)&mask
    return h
def read(tag,arm):
    s=(d/f'{tag}-{arm}.log').read_text()
    assert 'reason=verified 120 original demo frames' in s
    rows=[(int(f),int(sets),int(total),int(n),int(h,16)) for f,sets,total,n,h in
          re.findall(r'^\[RNG_PRESENT\] (\d+) 1 (\d+) \d+ (\d+) (\d+) ([0-9a-f]+)$',s,re.M)]
    assert len(rows)>100 and rows[0][3:]==(0,digest([])) and len({r[1] for r in rows})==1
    assert all(b[2]-a[2]==b[3] for a,b in zip(rows,rows[1:]))
    values=[];state=1
    for _ in range(rows[-1][2]):
        state=(state*0x343fd+0x269ec3)&0xffffffff
        values.append((state>>16)&0x7fff)
    first=rows[1]
    offsets=[j for j in range(rows[0][2]+1) if digest(values[j:j+first[3]])==first[4]]
    assert len(offsets)==1
    offset,=offsets
    for frame,_,total,n,h in rows:
        end=offset+total-rows[0][2]
        assert digest(values[end-n:end])==h,(tag,arm,frame)
    return rows,offset
for tag in ('cumulative-one','paced-cumulative'):
    for i in (1,2):
        (a,x),(b,y)=[read(tag,f'{arm}-{i}') for arm in ('original','split')]
        assert x==y
        pairs=list(zip(a[1:],b[1:]))
        diffs=[(v[2]-b[0][2])-(u[2]-a[0][2]) for u,v in pairs]
        first=next((k for k,n in enumerate(diffs) if n),None)
        last=next((k for k in range(len(diffs)-1,-1,-1) if diffs[k]==0),None)
        print(tag,i,'offset',x,'verified intervals',len(a)-1,len(b)-1,'first nonzero ordinal',None if first is None else first+1,
              'last equal ordinal',None if last is None else last+1,'common-end ordinal/FIFOs/delta',
              len(diffs),pairs[-1][0][0],pairs[-1][1][0],diffs[-1])
