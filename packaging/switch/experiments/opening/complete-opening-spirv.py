"""Append only missing opening sources to a separate candidate cache, retaining the original prefix."""
import sys,re,struct
from pathlib import Path
old,add,log,out=map(Path,sys.argv[1:])
assert out.resolve() not in (old.resolve(),add.resolve())
def records(data):
    assert data[:8]==b'NGBD3DC1'
    rows={};i=8
    while i<len(data):
        h,n=struct.unpack_from('<QI',data,i);i+=12
        words=data[i:i+n*4];i+=n*4
        assert len(words)==n*4 and n>=5 and words[:4]==bytes.fromhex('03022307')
        j=5
        while j<n:
            count=struct.unpack_from('<I',words,4*j)[0]>>16
            assert count>0
            j+=count
        assert j==n and rows.get(h,words)==words
        rows[h]=words
    return rows
s=log.read_text();assert 'reason=verified 120 original demo frames' in s
requests=re.findall(r'^\[RECIPE_SOURCE\] [FVP] ([a-f0-9]+) ([a-f0-9]+) (\d+)$',s,re.M)
assert len({k for k,h,n in requests})==118
base=old.read_bytes();known=records(base);extra=records(add.read_bytes())
need={int(h,16):int(n) for k,h,n in requests}
missing=sorted(need.keys()-known.keys())
assert missing and set(missing)<=extra.keys()
result=base+b''.join(struct.pack('<QI',h,len(extra[h])//4)+extra[h] for h in missing)
final=records(result);assert all(len(final[h])==4*n for h,n in need.items())
out.write_bytes(result)
print('added records',len(missing),'added bytes',len(result)-len(base))
