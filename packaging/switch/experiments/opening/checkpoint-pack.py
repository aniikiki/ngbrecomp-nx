"""Place independently exported checkpoint counters together; preserve every update and callback."""
from pathlib import Path
import subprocess
fields=[('ngb_reg_entries',0,8),('ngb_guest_polls',8,8),('ngb_reg_current_va',16,4),('ngb_poll_mask',20,4),('ngb_pending_dpcs',24,4),('ngb_reg_recent',32,128)]
def emit(s):
    k='\tadrp\tx2, ngb_reg_entries'
    assert s.count(k)==1
    s=s.replace(k,k+'\n\tadd x2,x2,:lo12:ngb_reg_entries')
    for name,off,_ in fields:
        if name!='ngb_reg_entries':
            reg='x3' if name=='ngb_reg_current_va' else 'x2' if name=='ngb_reg_recent' else 'x1'
            k=f'\tadrp\t{reg}, {name}\n';assert s.count(k)==1
            s=s.replace(k,'')
        if name=='ngb_reg_recent':
            k='\tadd\tx2, x2, :lo12:ngb_reg_recent\n\tstr\tw0, [x2, x1, lsl 2]'
            assert s.count(k)==1;s=s.replace(k,'\tadd x4,x2,32\n\tstr w0,[x4,x1,lsl 2]')
        else:
            import re
            s,n=re.subn(r'\[x[123], #:lo12:'+name+r'\]',f'[x2,#{off}]',s);assert n==(2 if name in ('ngb_reg_entries','ngb_guest_polls') else 1)
    storage='\n.pushsection .data.opening_counters,"aw",%progbits\n.balign 64\n'
    pos=0
    for name,off,size in fields:
        if off>pos:storage+=f'.zero {off-pos}\n'
        storage+=f'.global {name}\n.type {name},%object\n{name}:\n'
        storage+=('.word 3\n' if name=='ngb_poll_mask' else f'.zero {size}\n')
        storage+=f'.size {name},{size}\n';pos=off+size
    return s+storage+'.popsection\n'
def install(p,regs,src):
    rt=(p.out/'host-runtime.inc').read_text()
    for old,new in [('__attribute__((visibility("hidden"))) uint32_t current_va, recent[32];','extern uint32_t current_va, recent[32];'),('__attribute__((visibility("hidden"))) uint64_t entries;','extern uint64_t entries;'),('uint64_t ngb_guest_polls;','extern uint64_t ngb_guest_polls;'),('unsigned ngb_poll_mask = 3;','extern unsigned ngb_poll_mask;'),('unsigned ngb_pending_dpcs;','extern unsigned ngb_pending_dpcs;')]:
        assert rt.count(old)==1;rt=rt.replace(old,new)
    (p.out/'packed-runtime.inc').write_text(rt)
    out=p.out/'packed-checkpoint.S';out.write_text(emit((Path(__file__).resolve().parents[2]/'arm-registers/checkpoint.S').read_text()))
    obj=out.with_suffix('.o');subprocess.run(['cc','-c',out,'-o',obj],check=True)
    p.link[p.link.index(str(regs/'checkpoint.o'))]=str(obj)
    assert src.count('"host-runtime.inc"')==1
    return src.replace('"host-runtime.inc"','"packed-runtime.inc"')
