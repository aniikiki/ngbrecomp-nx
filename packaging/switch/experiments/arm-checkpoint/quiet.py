"""Measure the diagnostic entry/history overhead in isolation. Actual poll
tickets, interrupts and original callbacks are identical. Never use a quiet
frame to attribute crashes from the recent-entry ring."""
from pathlib import Path
import re,subprocess as sp,sys
h=Path(__file__).resolve().parent;perf=h.parents[1]/'perf';sys.path.insert(0,str(perf));from native_probe import *
p=NativeProbe('checkpoint-quiet');p.driver((perf/'trial.inc').read_text())
s=(h.parents[1]/'arm-registers/checkpoint.S').read_text()
a=s.index('\tadrp\tx1, ngb_guest_polls');b=s.index('.L5:',a);poll=s[a:b].replace('cbz\tw1, .L1','cbz\tw1, 3f').replace('beq\t.L5','beq\t2f')
k='ngb_reg_checkpoint:\n';s=s.replace(k,k+''' adrp x16,trial_variant
 ldr w16,[x16,:lo12:trial_variant]
 cbz w16,1f
 // The three functional event addresses are handled by the unmodified entry.
 mov w16,#0xa010
 movk w16,#0x17,lsl #16
 cmp w0,w16
 b.eq 1f
 mov w16,#0xdc50
 movk w16,#0x31,lsl #16
 cmp w0,w16
 b.eq 1f
 mov w16,#0xc310
 movk w16,#0x3c,lsl #16
 cmp w0,w16
 b.eq 1f
 adrp x16,ngb_reg_entries
 ldr x17,[x16,:lo12:ngb_reg_entries]
 add x17,x17,#1
 str x17,[x16,:lo12:ngb_reg_entries]
 adrp x16,ngb_reg_current_va
 str w0,[x16,:lo12:ngb_reg_current_va]
'''+poll+'''2:
 b ngb_gate_ngb_poll_due
3: ret
1:
''');f=p.out/'fast.S';f.write_text(s);o=p.out/'fast.o';sp.run(['cc','-c',f,'-o',o],check=True);p.link[p.link.index(str(REGS/'checkpoint.o'))]=str(o);p.link.insert(1,'-Wl,--strip-debug')
s=(RUNTIME/'scene/bridge.c').read_text();k='    ++scene_flips;';p.add('scene/bridge.c',s.replace(k,k+' extern void ngb_trial_flip(unsigned,unsigned);ngb_trial_flip(scene_flips,draws);'));p.finish()
