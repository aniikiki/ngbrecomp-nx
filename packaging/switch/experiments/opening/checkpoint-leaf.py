"""Keep entry history and poll order exact. Save LR only on the two call paths.
Use a negative filter before loading three startup addresses on every entry."""
from pathlib import Path
import subprocess
def emit(s):
    events=(0x17a010,0x31dc50,0x3cc310)
    mask=sum(1<<i for i in {a>>14&31 for a in events})
    # The mask only rules addresses OUT; a matching bucket still uses all original comparisons.
    assert mask==0x40080080
    a=s.index('\tstp\tx29, x30');b=s.index('\tadrp\tx2, ngb_reg_entries',a)
    pro=s[a:b]+'\tmov x29,sp\n'
    s=s[:a]+s[b:]
    s=s.replace('\tmov\tx29, sp\n','')
    key='\tmov\tw3, 40976';assert s.count(key)==1
    s=s.replace(key,f'\tubfx w4,w0,#14,#5\n\tmovz w3,#{mask&65535}\n\tmovk w3,#{mask>>16},lsl #16\n\tlsrv w3,w3,w4\n\ttbz w3,#0,.Lordinary\n'+key)
    s=s.replace('\tadrp\tx3, ngb_reg_current_va','.Lordinary:\n\tadrp\tx3, ngb_reg_current_va')
    a=s.index('.L5:\n');b=s.index('.L2:\n',a)
    s=s[:a]+'\tb .L5\n.L1:\n\tret\n.L5:\n\tb ngb_gate_ngb_poll_due\n'+s[b:]
    s=s.replace('.L2:\n\t.cfi_restore_state\n','.L2:\n'+pro)
    return s
def install(p,regs):
    path=p.out/'checkpoint-leaf.S'
    path.write_text(emit((Path(__file__).resolve().parents[2]/'arm-registers/checkpoint.S').read_text()))
    obj=path.with_suffix('.o')
    subprocess.run(['cc','-c',path,'-o',obj],check=True)
    p.link[p.link.index(str(regs/'checkpoint.o'))]=str(obj)
