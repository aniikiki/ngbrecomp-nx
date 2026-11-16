"""Compare code section contents and exported guest ABI for this one compile hint."""
import struct,sys
from pathlib import Path
d=Path('build/switch-runtime/core-perf')
def inspect(path):
    buf=path.read_bytes()
    def un(fmt,pos):return struct.unpack_from('<'+fmt,buf,pos)
    sections=[un('IIQQQQIIQQ',un('Q',40)[0]+64*i) for i in range(un('H',60)[0])]
    def name(sec,off):
        i=sec[4]+off
        return buf[i:buf.index(b'\0',i)].decode()
    names=sections[un('H',62)[0]]
    text={name(names,s[0]):buf[s[4]:s[4]+s[5]] for s in sections if s[2]&4 and s[5]}
    public=set()
    for s in sections:
        if s[1]!=2:continue
        for pos in range(s[4],s[4]+s[5],24):
            off,info,_,idx,_,_=un('IBBHQQ',pos)
            if idx and info==0x12:public.add(name(sections[s[6]],off))
    return text,public
changed=old=new=cold=0
literal='--literal-xmm' in sys.argv
for u in ((2,10,16,26) if literal else (2,10,16,26,39)):
    name=f'recomp_{u:04}.c.o'
    a,ap=inspect(d/'opening-compact-loops'/name)
    b,bp=inspect(d/('opening-literal-xmm' if literal else 'opening-cold-scalar')/name)
    assert ap and ap==bp,(ap-bp,bp-ap)
    changed+=sum(a.get(k)!=b.get(k) for k in a.keys()|b.keys())
    old+=sum(map(len,a.values()));new+=sum(map(len,b.values()))
    cold+=sum(len(v) for k,v in b.items() if 'unlikely' in k)
print('executable bytes before/after',old,new,'changed sections',changed,'candidate .unlikely bytes',cold)

if literal and not changed:raise SystemExit(3)
