"""Check ELF relocations of register-ABI units, without dumping megabytes of
assembly. Public callback addresses are allowed; a call to another covered
guest's public wrapper would reload stale g_regs. Private addresses must not
be handed to ordinary host code through an address table."""
import argparse
import re
from pathlib import Path
from struct import unpack_from, iter_unpack
from collections import Counter

guest = re.compile(r'(?:sub_[0-9A-F]+|d3d_orig_[0-9A-F]+|xbe_entry_point)$')
def inspect(path):
    data = path.read_bytes()
    assert data[:6] == b'\x7fELF\x02\x01' and unpack_from('<H',data,18)[0]==183,path
    pos = unpack_from('<Q',data,40)[0]
    size, count, names = unpack_from('<HHH',data,58)
    sections=[unpack_from('<IIQQQQIIQQ',data,pos+size*i) for i in range(count)]
    def contents(sec):return memoryview(data)[sec[4]:sec[4]+sec[5]]
    def lookup(string_table):
        s=contents(string_table).tobytes()
        def at(ix):return s[ix:s.index(b'\0',ix)].decode()
        return at
    secname=lookup(sections[names]); metrics=Counter();issues=[];defs=set()
    for sec in sections:
        if sec[1]!=2:continue
        symname=lookup(sections[sec[6]])
        symbols=[(symname(n),kind,idx) for n,kind,other,idx,val,sz in iter_unpack('<IBBHQQ',contents(sec))]
        defs.update(n for n,k,i in symbols if i and k>>4 and k&15==2)
        # Relocations must refer to this particular symbol table.
        for rel in sections:
            if rel[1]!=4 or sections[rel[6]]!=sec:continue
            target=sections[rel[7]]
            if not target[2]&2 or secname(target[0])=='.eh_frame':continue
            for off,info,add in iter_unpack('<QQq',contents(rel)):
                ty=info&0xffffffff;n=symbols[info>>32][0]
                priv=n.startswith('ngb_reg_');g=n[8:] if priv else n
                if not guest.fullmatch(g):continue
                branch=ty in (282,283)
                label=('private' if priv else 'public')+('-branch' if branch else '-address')
                metrics[label]+=1
                if (priv and not branch) or (not priv and branch):
                    issues.append((label,n,secname(target[0]),off))
    return defs,metrics,issues

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('directory',type=Path);ap.add_argument('--units',type=int,required=True)
    args=ap.parse_args();d=args.directory
    entries=inspect(d/'entry.o')[0];entries={n for n in entries if guest.fullmatch(n)}
    units=sorted(d.glob('recomp_*.c.o'));assert len(units)==args.units
    metrics=Counter();defs=set();bad=[]
    for p in units:
        syms,counts,issues=inspect(p);defs.update(n[8:] for n in syms if n.startswith('ngb_reg_'))
        metrics.update(counts)
        bad.extend((p.name,row) for row in issues if row[0]=='private-address' or row[1] in entries)
    print('units',len(units),'public wrappers',len(entries),'private entries',len(defs),dict(metrics))
    assert defs==entries,(sorted(defs-entries)[:8],sorted(entries-defs)[:8])
    assert not bad,(len(bad),bad[:12])
