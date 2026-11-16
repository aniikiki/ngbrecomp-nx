"""Sample inclusive parent/child CPU time; independently inspect repeated entry fields."""
from pathlib import Path
import sys,subprocess
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'perf'))
from native_probe import *
p=NativeProbe('opening-setup')
if '--separate' in sys.argv:
 p.out=p.core/'predicate-budget';p.out.mkdir(exist_ok=True)
s=(REGS/'recomp_0002.c.gated.s').read_text()
for name,tag in [('0003B420','parent'),('0003AE90','child')]:
 k='ngb_reg_sub_'+name+':\n';assert s.count(k)==1
 # Entry ABI has guest values in x19..x28. Return ABI only changes the guest
 # register file. Before original code, no C call may disturb guest registers.
 gate=''' adrp x16,pred_on
 ldr w17,[x16,:lo12:pred_on]
 cbz w17,.Lbase_NAME
'''
 if tag=='parent':
  gate+=''' cmp w17,#2
 b.eq .Ltrace_NAME
 adrp x16,pred_n
 ldr w17,[x16,:lo12:pred_n]
 add w17,w17,#1
 str w17,[x16,:lo12:pred_n]
 // Weyl sequence high bits; randomize phase each frame.
 adrp x16,pred_rand
 ldr w17,[x16,:lo12:pred_rand]
 mov w15,#0x79b9
 movk w15,#0x9e37,lsl #16
 add w17,w17,w15
 str w17,[x16,:lo12:pred_rand]
 lsr w17,w17,#27
 cbnz w17,.Lbase_NAME
.Ltrace_NAME:
'''
 else:
  gate+=''' adrp x16,pred_inside
 ldr w17,[x16,:lo12:pred_inside]
 cbz w17,.Lbase_NAME
'''
 gate+=''' stp x29,x30,[sp,#-16]!
 mov x0,x26
 mov w1,w20
 mov w2,w21
 mov w3,w22
 mov w4,w19
 bl pred_NAME_in
 bl .Lbase_NAME
 mov w0,w19
 bl pred_NAME_out
 ldp x29,x30,[sp],#16
 ret
.Lbase_NAME:
'''
 s=s.replace(k,k+gate.replace('NAME',tag))
f=p.out/'pred-budget.s';o=f.with_suffix('.o');f.write_text(s)
subprocess.run(['cc','-c',f,'-o',o],check=True);p.link[p.link.index(str(REGS/'recomp_0002.c.o'))]=str(o)
p.driver(Path(__file__).with_name('predicate-budget.inc').read_text())
s=(RUNTIME/'scene/bridge.c').read_text()
for k,arg in [('            ngb_direct_reset_stats();','0'),('    ++scene_flips;','scene_flips')]:
 assert s.count(k)==1;s=s.replace(k,k+f' extern void pred_flip(unsigned);pred_flip({arg});')
p.add('scene/bridge.c',s);p.link.insert(1,'-Wl,--strip-debug');p.finish()
