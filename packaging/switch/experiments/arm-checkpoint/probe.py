"""Change the entry path without changing even one interrupt or recent-PC slot.
Paired offline replay. Both arms share the same compact writable state layout."""
from pathlib import Path
import sys,subprocess as sp
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'perf'))
from native_probe import NativeProbe,ROOT,REGS,RUNTIME
p=NativeProbe('checkpoint-state')
s=(REGS/'host-runtime.inc').read_text()
for n in ('RecompRegs g_regs;', 'uint64_t ngb_guest_polls;', 'unsigned ngb_poll_mask = 3;', 'unsigned ngb_pending_dpcs;', 'uint32_t current_va, recent[32];','uint64_t entries;'):
 s=s.replace(n,'extern '+n.replace(' = 3',''))
s=s.replace('static extern ','static ')
(p.out/'host-runtime.inc').write_text(s)
s+='\n_Static_assert(sizeof(RecompRegs)<=512 && _Alignof(RecompRegs)<=16,"state layout");\n'
(p.out/'host-runtime.inc').write_text(s)
p.driver((ROOT/'packaging/switch/perf/trial.inc').read_text())
orig=(RUNTIME.parent/'arm-registers/checkpoint.S').read_text().replace('ngb_reg_checkpoint','original_reg_checkpoint')
# Regfile starts 176 bytes after the state block and is at least 16-byte aligned.
head="""
.data
.balign 64
.global ngb_reg_entries,ngb_guest_polls,ngb_poll_mask,ngb_pending_dpcs,ngb_reg_current_va,ngb_reg_recent,g_regs
ngb_reg_entries: .quad 0
ngb_guest_polls: .quad 0
ngb_poll_mask: .word 3
ngb_pending_dpcs: .word 0
ngb_reg_current_va: .word 0
.space 4
ngb_reg_recent: .space 128
.space 16
g_regs: .space 512
.text
.balign 32
.global ngb_reg_checkpoint
ngb_reg_checkpoint:
 adrp x16,trial_variant
 ldr w16,[x16,:lo12:trial_variant]
 cbz w16,original_reg_checkpoint
 sub x9,x28,#176
 ldp x1,x2,[x9]
 cmp x1,#48
 b.lo original_reg_checkpoint
 mov w4,#0xa010
 movk w4,#0x17,lsl 16
 cmp w0,w4
 mov w4,#0xdc50
 movk w4,#0x31,lsl 16
 ccmp w0,w4,#4,ne
 mov w4,#0xc310
 movk w4,#0x3c,lsl 16
 ccmp w0,w4,#4,ne
 b.eq original_reg_checkpoint
 and x3,x1,#31
 add x1,x1,#1
 add x2,x2,#1
 stp x1,x2,[x9]
 str w0,[x9,#24]
 add x4,x9,#32
 str w0,[x4,x3,lsl 2]
 ldp w3,w4,[x9,#16]
 tst x2,x3
 ccmp w4,#0,#0,ne
 b.ne 1f
 ret
1:
 mov x0,x2
 stp x29,x30,[sp,#-16]!
 mov x29,sp
 stp w19,w20,[x28]
 stp w21,w22,[x28,#8]
 stp w23,w24,[x28,#16]
 str w25,[x28,#24]
 bl ngb_poll_due
 ldp w19,w20,[x28]
 ldp w21,w22,[x28,#8]
 ldp w23,w24,[x28,#16]
 ldr w25,[x28,#24]
 ldp x29,x30,[sp],#16
 ret
"""
a=p.out/'checkpoint.s';a.write_text(head+orig)
o=p.out/'checkpoint.o';sp.run(['cc','-c',a,'-o',o],check=True)
p.link[p.link.index(str(REGS/'checkpoint.o'))]=str(o)
s=(RUNTIME/'scene/bridge.c').read_text();k='    ++scene_flips;';assert s.count(k)==1
p.add('scene/bridge.c',s.replace(k,k+' extern void ngb_trial_flip(unsigned,unsigned);ngb_trial_flip(scene_flips,draws);'))
p.finish()
