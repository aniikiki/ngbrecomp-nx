"""Join the HLSL source/stage keys used in replay to the exact shipped SPIR-V table."""
from pathlib import Path
from struct import unpack_from
import re,sys
root=Path('build/switch-runtime')
d=root/'core-perf/opening-present-combined'
complete='--complete' in sys.argv
log=(d/('openingspirv-check.log' if complete else 'recipesources-warm-small-1.log')).read_text()
assert 'reason=verified 120 original demo frames' in log and '118 shaders and 167 pipelines made ahead' in log
seed=(root/'romfs/.ngb-spirv').read_bytes()
assert seed==(root/'direct/cache/spirv.bin').read_bytes()
if complete:
    candidate=(d/'opening-complete.spirv').read_bytes();assert candidate.startswith(seed);seed=candidate
assert seed[:8]==b'NGBD3DC1'
cache={};i=8
while i<len(seed):
    key,n=unpack_from('<QI',seed,i); i+=12
    assert n>=5 and i+4*n<=len(seed) and unpack_from('<I',seed,i)[0]==0x07230203
    cache[key]=n;i+=4*n
rows=[(k,int(a,16),int(b,16),int(n)) for k,a,b,n in re.findall(r'^\[RECIPE_SOURCE\] ([FVP]) ([a-f0-9]+) ([a-f0-9]+) (\d+)$',log,re.M)]
assert len(rows)==len({a for _,a,_,_ in rows})==118
for k in 'FVP':
    r=[(b,n) for kind,a,b,n in rows if kind==k]
    print(k,'recipe modules',len(r),'source keys',len(set(b for b,_ in r)),'modules matching packaged key + word count',sum(cache.get(b)==n for b,n in r))
needed={b for _,_,b,_ in rows}
print('packaged',len(cache),'needed distinct',len(needed),'missing',len(needed-cache.keys()),'unused',len(cache.keys()-needed))
