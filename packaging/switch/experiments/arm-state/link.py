"""Pair regular and state-relative private game objects in the same guest scene."""
from pathlib import Path
import subprocess as sp,sys,re
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent.parent/'perf'))
from native_probe import NativeProbe,BASE,REGS,ROOT,RUNTIME
d=BASE/'opt050/state';p=NativeProbe('inline-state')
trial=(ROOT/'packaging/switch/perf/trial.inc').read_text()
rt=(REGS/'host-runtime.inc').read_text()
for decl in ('RecompRegs g_regs;', 'uint64_t ngb_guest_polls;', 'unsigned ngb_poll_mask = 3;', 'unsigned ngb_pending_dpcs;', 'uint32_t current_va, recent[32];','uint64_t entries;'):
    rt=rt.replace(decl,'extern '+decl.replace(' = 3',''))
rt=rt.replace('static extern ','static ')
(p.out/'host-runtime.inc').write_text(rt)
p.driver(trial)
layout=p.out/'layout.s'
layout.write_text(""".data
.balign 64
.global g_regs,ngb_reg_entries,ngb_guest_polls,ngb_poll_mask,ngb_pending_dpcs,ngb_reg_current_va,ngb_reg_recent
g_regs: .space 512
ngb_reg_entries: .quad 0
ngb_guest_polls: .quad 0
ngb_poll_mask: .word 3
ngb_pending_dpcs: .word 0
ngb_reg_current_va: .word 0
ngb_reg_recent: .space 128
.section .note.GNU-stack,"",%progbits
""")
obj=p.out/'layout.o';sp.run(['cc','-c',layout,'-o',obj],check=True);p.link.insert(1,str(obj))
public=set(re.findall(r'^((?:sub_|d3d_orig_)[0-9A-F]+):$',(REGS/'entry.S').read_text(),re.M))
assert len(public)>3000
for prefix,root in [('a',d),('b',REGS)]:
    objs=sorted(root.glob('recomp_*.c.o'))+[root/'gates.o',root/'entry.o']
    assert len(objs)==16
    names=set(public)
    for o in objs:
        out=sp.check_output(['nm','-g','--defined-only',o],text=True)
        names.update(l.split()[-1] for l in out.splitlines() if l.strip() and l.split()[-1].startswith(('ngb_reg_','ngb_gate_')))
    # ngb_reg_checkpoint's implementation is shared. Both ARM ABIs preserve x27
    # through poll callbacks, and the checkpoint doesn't consult either page table.
    names.discard('ngb_reg_checkpoint')
    sy=p.out/(prefix+'.map');sy.write_text(''.join(f'{n} {prefix}_{n}\n' for n in sorted(names)))
    for o in objs:
        new=p.out/(prefix+'-'+o.name)
        sp.run(['objcopy','--strip-debug','--redefine-syms='+str(sy),o,new],check=True)
        if prefix=='b':p.link[p.link.index(str(o))]=str(new)
        else:p.link.insert(1,str(new))
s=p.out/'select.s'
s.write_text('.text\n'+''.join(f'.global {n}\n.type {n},%function\n{n}:\n adrp x16,trial_variant\n ldr w16,[x16,:lo12:trial_variant]\n cbnz w16,1f\n b b_{n}\n1: b a_{n}\n' for n in sorted(public))+'.section .note.GNU-stack,"",%progbits\n')
o=p.out/'select.o';sp.run(['cc','-c',s,'-o',o],check=True);p.link.insert(1,str(o))
s=(RUNTIME/'scene/bridge.c').read_text();marker='    ++scene_flips;'
assert s.count(marker)==1
p.add('scene/bridge.c',s.replace(marker,marker+' extern void ngb_trial_flip(unsigned,unsigned);ngb_trial_flip(scene_flips,draws);'))
p.finish()
