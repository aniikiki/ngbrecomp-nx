"""Collect temporal guest entry transitions, not call edges. Unchanged guest ABI."""
from pathlib import Path
import subprocess
def install(p,regs,stack_site=False):
 s=(Path(__file__).resolve().parents[2]/'arm-registers/checkpoint.S').read_text()
 k='\tadrp\tx2, ngb_reg_entries';assert s.count(k)==1
 # C arguments and caller-saved registers are already volatile across checkpoint;
 # explicitly retain its VA argument. The original frame already saved LR.
 s=s.replace(k,''' adrp x1,stream_on
 ldr w1,[x1,:lo12:stream_on]
 cbz w1,.Lstream_done
 str x0,[sp,#-16]!
 bl stream_visit
 ldr x0,[sp],#16
.Lstream_done:
'''+k)
 if stack_site:
  s=s.replace(' bl stream_visit',' mov w1,w22\n mov x2,x26\n mov x3,x27\n mov w4,w20\n mov w5,w21\n bl stream_visit')
 f=p.out/'stream.S';f.write_text(s);o=f.with_suffix('.o');subprocess.run(['cc','-c',f,'-o',o],check=True)
 p.link[p.link.index(str(regs/'checkpoint.o'))]=str(o)
