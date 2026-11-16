"""Check flat RomFS assets by their actual metadata and verify pipeline dependencies."""
from pathlib import Path
from struct import unpack_from
import sys
cache=Path('build/switch-runtime/direct/cache')
def files(b):
    size,_,_,_,_,_,_,off,n,data=unpack_from('<10Q',b)
    assert size==80 and off+n<=len(b)
    entries={};i=0
    while i<n:
        parent,_,pos,length,_,namesize=unpack_from('<IIQQII',b,off+i)
        assert parent==0 and i+32+namesize<=n and data+pos+length<=len(b)
        name=b[off+i+32:off+i+32+namesize].decode()
        assert name not in entries
        entries[name]=b[data+pos:data+pos+length]
        i+=(32+namesize+3)&~3
    assert i==n
    return entries
with Path(sys.argv[1]).open('rb') as f:
    f.seek(24);aset=unpack_from('<I',f.read(4))[0];f.seek(aset);assert f.read(4)==b'ASET'
    f.seek(aset+40);off,n=unpack_from('<QQ',f.read(16));f.seek(aset+off)
    old=files(f.read(n))
spv=(cache/'spirv.bin').read_bytes()
assert old=={'.ngb-spirv':spv}
seed=(Path(sys.argv[3]) if len(sys.argv)>3 else cache/'recipes.bin').read_bytes()
if len(sys.argv)>4:
    packed=Path(sys.argv[4]).read_bytes();assert packed.startswith(spv);spv=packed
assert files(Path(sys.argv[2]).read_bytes())=={'.ngb-spirv':spv,'.ngb-recipes':seed}
assert seed[:8]==b'NGBD3DC1'
i=8;modules={};pipes=[]
while i<len(seed):
    kind,key,n=unpack_from('<cQI',seed,i);i+=13
    assert i+n<=len(seed)
    if kind==b'K':
        assert n==256
        pipes.append(unpack_from('<QQ',seed,i))
    else:
        assert kind in (b'V',b'F',b'P')
        modules[key]=kind
    i+=n
assert pipes and all(modules.get(v) in (b'V',b'F') and modules.get(p)==b'P' for v,p in pipes)
print(len(seed),'recipe bytes;',len(modules),'module keys;',len(pipes),'pipeline records with both keys present')
