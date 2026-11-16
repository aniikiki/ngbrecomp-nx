"""Pair two private-register builds in one real combat. No alternate ARM guest
may enter the other one's private ABI: x27 deliberately has a different type."""
from pathlib import Path
import subprocess as sp,sys,re
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent.parent/'perf'))
from native_probe import NativeProbe,BASE,REGS,ROOT,RUNTIME
d=BASE/'opt050/bias';p=NativeProbe('bias');sources=d/'host-src'
trial=(ROOT/'packaging/switch/perf/trial.inc').read_text()
p.driver(trial)
for n in ('vm.c','contiguous.c'):
    # These services must use the public ABI. Never include the private game header.
    original=p.compile(n,(sources/n).read_text())
    # Some dependencies are in the archive, others explicitly on the exact link.
    matches=[j for j,v in enumerate(p.link) if v.endswith('/'+n+'.o')]
    if len(matches)==1:p.link[matches[0]]=original
    elif not matches:p.link.insert(1,original)
    else:raise ValueError((n,matches))
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
