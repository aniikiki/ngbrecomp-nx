"""Overlap the ordinary checkpoint's independent poll loads with ring bookkeeping."""
from pathlib import Path
import subprocess
def emit(s):
 a=s.index('\tadrp\tx3, ngb_reg_current_va');b=s.index('\n.L5:',a)
 old=s[a:b];assert old.count('ngb_poll_mask')==2 and old.count('ngb_pending_dpcs')==2
 ring=old[:old.index('\tadrp\tx1, ngb_guest_polls')]
 return s[:a]+'''\tadrp x4,ngb_guest_polls
    ldr x5,[x4,:lo12:ngb_guest_polls]
    adrp x6,ngb_poll_mask
    ldr w6,[x6,:lo12:ngb_poll_mask]
    adrp x7,ngb_pending_dpcs
    ldr w7,[x7,:lo12:ngb_pending_dpcs]
'''+ring+'''    add x0,x5,#1
    str x0,[x4,:lo12:ngb_guest_polls]
    tst x6,x0
    ccmp w7,#0,#0,ne
    b.eq .L1
'''+s[b:]
def install(p,regs):
 s=(Path(__file__).resolve().parents[2]/'arm-registers/checkpoint.S').read_text()
 out=p.out/'checkpoint-loads.S';out.write_text(emit(s));obj=out.with_suffix('.o')
 subprocess.run(['cc','-c',out,'-o',obj],check=True)
 p.link[p.link.index(str(regs/'checkpoint.o'))]=str(obj)
