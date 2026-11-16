"""Compare recorded pipeline keys by all bytes, as in PipeKey::operator==."""
from pathlib import Path
from struct import unpack_from

def read(p):
    b=p.read_bytes()
    assert b[:8]==b'NGBD3DC1'
    i=8; m={};pipes=set()
    while i<len(b):
        k,key,n=unpack_from('<cQI',b,i);i+=13
        assert i+n<=len(b)
        v=b[i:i+n];i+=n
        if k==b'K':
            assert len(v)==256
            pipes.add(v)
        else:
            assert k in (b'V',b'F',b'P') and m.get(key,(k,v))==(k,v)
            m[key]=(k,v)
    assert all(m[v][0] in (b'V',b'F') and m[p][0]==b'P' for v,p in map(lambda x:unpack_from('<QQ',x),pipes))
    return m,pipes

d=Path('build/switch-runtime/core-perf/opening-present-combined')
front,opening,old=[read(p) for p in (d/'opening-30.recipes',d/'opening-120.recipes',Path('build/switch-runtime/direct/cache/recipes.bin'))]
assert front[1]<=opening[1] and all(opening[0][k]==v for k,v in front[0].items())
for name,(m,ps) in [('front30',front),('opening120',opening)]:
    missing=ps-old[1]
    print(name,'covered by 180-record seed',len(ps&old[1]),'missing',len(missing),'missing modules',len(m.keys()-old[0].keys()),
          'missing pipes referencing absent modules',sum(any(k not in old[0] for k in unpack_from('<QQ',p)) for p in missing))
    assert all(old[0][k]==m[k] for k in m.keys()&old[0].keys())
print('following 90 newly required keys: modules',len(opening[0])-len(front[0]),'pipes',len(opening[1]-front[1]))

if __name__=='__main__':
    import re
    for log in ('recipefirst30-warm-front-1','recipesubset-warm-small-1','recipesubset-warm-full-1'):
        s=(d/(log+'.log')).read_text()
        assert 'reason=verified 120 original demo frames' in s
        records=[tuple(map(int,m)) for m in re.findall(r'\[OPEN_CREATES\] present=(\d+) shader=(\d+) pipeline=(\d+) us=(\d+)',s)]
        assert [v[0] for v in records]==[1,30,120]
        warm=re.findall(r'(\d+) shaders and (\d+) pipelines made ahead',s)
        assert len(warm)==1
        print(log,'prebuilt modules/pipes',warm[0], 'actual creates to 30 / next 90 (modules,pipes,us)',
              records[1][1:],tuple(a-b for a,b in zip(records[2][1:],records[1][1:])))
