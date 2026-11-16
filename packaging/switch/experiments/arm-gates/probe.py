"""Specialize private-register ABI exits, without rebuilding the guest. Direct
ordinary low RAM (one page, full permission, nonempty) cannot run a callback.
Only a fallback exports the seven guest registers. Mesh accounting never
reads them. All other original gates and all guest instructions remain."""
from pathlib import Path
import sys,subprocess as sp
h=Path(__file__).resolve().parent;sys.path.insert(0,str(h.parents[1]/'perf'))
from native_probe import NativeProbe,REGS,RUNTIME
p=NativeProbe('gate-span');p.driver((h.parents[1]/'perf/trial.inc').read_text())
s=(REGS/'gates.s').read_text()
for name,fast in {
'ngb_guest_pointer':'''
 // w0 guest address, x1 byte count, x26 RAM and x27 permission table.
 // Exclude the literal tick counter and the dedicated alias windows.
 cbz x1, 1f
 cbz x26, 1f
 lsr w2,w0,#26
 cbnz w2,1f
 lsr w2,w0,#12
 ldrh w3,[x27,x2,lsl #1]
 and w2,w0,#4095
 subs w3,w3,w2
 b.mi 1f
 cmp x1,x3
 b.hi 1f
 add x0,x26,w0,uxtw
 ret
''',
'ngb_direct_mesh_scope':' b ngb_direct_mesh_scope\n',
}.items():
 tag='ngb_gate_'+name+':\n';assert s.count(tag)==1
 s=s.replace(tag,tag+' adrp x16,trial_variant\n ldr w16,[x16,:lo12:trial_variant]\n cbz w16,1f\n'+fast+'1:\n')
o=p.out/'gates.o';f=p.out/'probe.S';f.write_text(s);sp.run(['cc','-c',f,'-o',o],check=True);p.link[p.link.index(str(REGS/'gates.o'))]=str(o)
s=(RUNTIME/'scene/bridge.c').read_text();k='    ++scene_flips;';p.add('scene/bridge.c',s.replace(k,k+' extern void ngb_trial_flip(unsigned,unsigned);ngb_trial_flip(scene_flips,draws);'));p.finish()
