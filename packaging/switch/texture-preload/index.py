"""Describe static 2D textures in retail KMD/XPR members; embed offsets, never pixels."""
import struct
from pathlib import Path
def emit(root,out):
    rows=[];names=[]
    bits={0:8,1:8,2:16,3:16,4:16,5:16,6:32,7:32,0x19:8,0x1a:16}
    for p in sorted(root.glob('*.afs')):
        with p.open('rb') as f:
            h=f.read(8)
            if h[:4]!=b'AFS\0':continue
            entries=list(struct.iter_unpack('<II',f.read(8*int.from_bytes(h[4:],'little'))))
            got=set()
            for o,n in entries:
                f.seek(o)
                if f.read(4)!=b'KMD\0':continue
                f.seek(o);b=f.read(n);x=b.find(b'XPR0')
                if x<0 or x+12>n:continue
                total,head=struct.unpack_from('<II',b,x+4)
                if not 12<=head<=total<=n-x:continue
                for i in range(x+12,x+head-19,4):
                    c,d,l,fmt,size=struct.unpack_from('<5I',b,i);typ=fmt>>8&255
                    if c!=0x40001 or l or size or fmt&4 or fmt>>4&15!=2:continue
                    w=1<<(fmt>>20&15);h=1<<(fmt>>24&15);lv=max(1,fmt>>16&15)
                    if w*h>262144 or lv>max(w,h).bit_length():continue
                    if typ not in (*bits,12,14,15):continue
                    length=0
                    for k in range(lv):
                        a=max(1,w>>k);v=max(1,h>>k)
                        length+=a*v*bits[typ]//8 if typ in bits else ((a+3)//4)*((v+3)//4)*(8 if typ==12 else 16)
                    if length<32 or length>524288 or head+d+length>total:continue
                    got.add((o+x+head+d,length,fmt))
            if got:
                names.append((p.name,len(rows),len(got)));rows.extend(sorted(got))
    assert names and rows
    out.write_text('static constexpr Slice slices[]={\n'+''.join('{%d,%d,0x%x},\n'%r for r in rows)+'};\nstatic constexpr Pack packs[]={\n'+''.join('{"%s",%d,%d},\n'%v for v in names)+'};\n')
