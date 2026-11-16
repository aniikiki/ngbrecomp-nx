"""Fast rejection of three rare event addresses without rewriting any guest calls."""
from pathlib import Path
import subprocess
def emit(s):
    k='\tmov\tw3, 40976';end='\tadrp\tx3, ngb_reg_current_va'
    mask=0xaf
    assert not any(a&mask for a in (0x17a010,0x31dc50,0x3cc310))
    assert s.count(k)==s.count(end)==1
    return s.replace(k,f'    mov w4,#{mask}\n    tst w0,w4\n    b.ne .Lordinary_mask\n'+k).replace(end,'.Lordinary_mask:\n'+end)
def install(p,regs):
 s=(Path(__file__).resolve().parents[2]/'arm-registers/checkpoint.S').read_text()
 out=p.out/'entry-mask.S';out.write_text(emit(s));obj=out.with_suffix('.o')
 subprocess.run(['cc','-c',out,'-o',obj],check=True)
 p.link[p.link.index(str(regs/'checkpoint.o'))]=str(obj)
