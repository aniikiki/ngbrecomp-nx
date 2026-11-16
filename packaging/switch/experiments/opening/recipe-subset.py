"""Extract a replay's first-use recipes only with verified complete record boundaries."""
import re,struct,sys
from pathlib import Path
from collections import Counter
raw,log,out=map(Path,sys.argv[1:]);s=log.read_text();data=raw.read_bytes()
assert 'verified 120 original demo frames' in s
m={int(f):int(o) for f,o in re.findall(r'^\[RECIPE_EXTENT\] (\d+) (\d+)$',s,re.M)}
assert set(m)=={1,30,120} and 8<=m[1]<=m[30]<=m[120]<=len(data)
def records(b):
    i=8
    while i<len(b):
        assert i+13<=len(b)
        kind=chr(b[i]);key,n=struct.unpack_from('<QI',b,i+1);j=i+13+n
        assert kind in 'VFPK' and j<=len(b)
        yield kind,key,b[i+13:j],b[i:j];i=j
for f in (1,30,120):
    rs=list(records(data[:m[f]]));mods={k for t,k,_,_ in rs if t!='K'}
    keys=[(a,b) for kind,k,blob,_ in rs if kind=='K' for a,b in [struct.unpack_from('<QQ',blob)] if a in mods and b in mods]
    used={x for pair in keys for x in pair}
    seed=data[:8]+b''.join(rec for kind,k,blob,rec in rs if (struct.unpack_from('<QQ',blob) in keys if kind=='K' else k in used))
    if f in (30,120):(out/f'opening-{f}.recipes').write_bytes(seed)
    print(f,'record counts',Counter(x[0] for x in rs),'usable pipes',len(keys),'required modules',len(used),'seed bytes',len(seed))
