"""Use the original table index to predict a local label. Keep the loaded
branch address authoritative, including when the game patches or aliases it."""
from pathlib import Path
import hashlib, os, re, struct, sys
base=Path('build/switch-runtime')
p=Path(__file__).resolve().parent
image=Path('game_files/default.xbe').read_bytes()
digest=re.search(r'#define NGB_IMAGE_SHA256 "([0-9a-f]{64})"',(base/'gen/ngb_image.h').read_text())[1]
assert hashlib.sha256(image).hexdigest()==digest
def word(off):return struct.unpack_from('<I',image,off)[0]
sections=[struct.unpack_from('<IIII',image,word(0x120)-word(0x104)+0x38*i+4) for i in range(word(0x11c))]
site=re.compile(r'(    \{ uint32_t _jt = MEM32\((e[a-z]{2}) \* 4 \+ (0x[0-9A-F]+)\); /\* switch: (\d+) entries, (\d+) targets \*/\n)((?:    if \(_jt == 0x[0-9A-F]+u\) goto loc_[0-9A-F]+;\n)+)')
def transform(s):
    stats=[]
    def one(m):
        header,reg,address,n,targets,arms=m.groups()
        if int(targets)<16:return m[0]
        addr=int(address,16); n=int(n)
        off,=[r+addr-v for v,vs,r,rs in sections if v<=addr and addr+4*n<=v+min(vs,rs)]
        labels={int(a,16):b for a,b in re.findall(r'if \(_jt == 0x([0-9A-F]+)u\) goto (loc_[0-9A-F]+);',arms)}
        assert len(labels)==int(targets)
        cases=[]
        for i in range(n):
            target=word(off+4*i)
            if target in labels:cases.append(f'    case {i}: if (_jt == 0x{target:08X}u) goto {labels[target]}; break;\n')
        stats.append((addr,len(cases)))
        return header+f'    switch ({reg}) {{\n'+''.join(cases)+'    }\n'+arms
    return site.sub(one,s),stats
if __name__=='__main__':
    src=(p/'vector-span.py').read_text().split("if __name__=='__main__':",1)[1]
    exec(compile('if True:'+src.replace('units=[16,28,29]','units=[0,2]').replace('opening-vector-span','opening-index-dispatch').replace('original vector moves','predicted entries'),'index-dispatch-build','exec'))
