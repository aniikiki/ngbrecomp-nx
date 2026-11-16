"""Opening experiment on top of the full guest register domain. Share the
public ABI save/restore sequence. Ordinary external and manual callbacks still
use the old gate. Only an exact address of a public slot may use its companion
private branch; keep the guest resolver and icall bookkeeping unchanged."""
from pathlib import Path
import re,subprocess as sp
def generate(src,gates):
    names=re.findall(r'^\.global (\w+)$',src,re.M)
    assert len(names)==len(set(names)) and 'xbe_entry_point' in names
    generic=None
    for match in re.finditer(r'^(\w+):\n(.*?)^\.size \1,',src,re.M|re.S):
        name,body=match.groups()
        assert body.count(' bl ngb_reg_'+name+'\n')==1
        body=body.replace(' bl ngb_reg_'+name+'\n',' blr x17\n')
        if generic is None:generic=body
        assert generic==body
    assert generic and src.count('\n.size ')==len(names)
    # No memory is read for target lookup. Linker may insert veneers for very
    # distant branches; the private branch takes no arguments in x16/x17.
    head='.text\n.p2align 4\n.hidden opening_slots\n.global opening_slots\nopening_slots:\n'
    entry=head+''.join(f'.global {n}\n.type {n},%function\n{n}:\n adrp x17,ngb_reg_{n}\n add x17,x17,:lo12:ngb_reg_{n}\n b opening_bridge\n b ngb_reg_{n}\n.size {n},.-{n}\n' for n in names)
    entry+=f'.if (. - opening_slots) != {len(names)*16}\n.error "unexpected slot width"\n.endif\n.type opening_bridge,%function\nopening_bridge:\n'+generic+'.size opening_bridge,.-opening_bridge\n.section .note.GNU-stack,"",%progbits\n'
    key='ngb_gate_indirect:\n'
    assert gates.count(key)==1
    # Don't use x0..x7: an indirect foreign target can inspect its arguments.
    n=len(names)*16
    gates=gates.replace(key,key+f''' adrp x17,opening_slots
 add x17,x17,:lo12:opening_slots
 sub x17,x16,x17
 movz x15,#{n&65535}
 movk x15,#{n>>16},lsl #16
 cmp x17,x15
 b.hs 1f
 tst x17,#15
 b.ne 1f
 add x16,x16,#12
 br x16
1:
''')
    return entry,gates
def install(p):
    d=p.core/'opening-full-guest';a,b=generate((d/'entry.S').read_text(),(d/'gates.s').read_text())
    for name,s in [('entry',a),('gates',b)]:
        f=p.out/('compact-'+name+'.S');f.write_text(s)
        obj=f.with_suffix('.o');sp.run(['cc','-c',f,'-o',obj],check=True)
        p.link[p.link.index(str(d/(name+'.o')))]=str(obj)
