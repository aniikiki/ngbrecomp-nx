"""Diagnostic only: bound the per-entry cost of maintaining the crash-history ring."""
from pathlib import Path
import subprocess
def install(p,regs):
    path=Path(__file__).resolve().parents[2]/'arm-registers/checkpoint.S'
    s=path.read_text()
    for line in ('and\tx1, x1, 31','adrp\tx2, ngb_reg_recent','add\tx2, x2, :lo12:ngb_reg_recent','str\tw0, [x2, x1, lsl 2]'):
        key='\t'+line+'\n';assert s.count(key)==1;s=s.replace(key,'')
    out=p.out/'history-cost.S';out.write_text(s);obj=out.with_suffix('.o')
    subprocess.run(['cc','-c',out,'-o',obj],check=True)
    p.link[p.link.index(str(regs/'checkpoint.o'))]=str(obj)
