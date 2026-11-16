"""Public function pointers keep one canonical value. In the private gate,
a pointer inside the aligned public slot array can jump directly to its
private entry. Kernel/manual/external pointers use the existing gate."""
from pathlib import Path
import re,sys,subprocess as sp
h=Path(__file__).resolve().parent;perf=h.parents[1]/'perf';sys.path.insert(0,str(perf));from native_probe import *
p=NativeProbe('paired-indirect');p.driver((perf/'trial.inc').read_text())
names=sorted(re.findall(r'^((?:sub_|d3d_orig_)[0-9A-F]+):$',(REGS/'entry.S').read_text(),re.M));assert len(names)>3000
m=p.out/'pub.map';m.write_text(''.join(f'{n} slow_{n}\n' for n in names));o=p.out/'slow.o';sp.run(['objcopy','--redefine-syms='+str(m),REGS/'entry.o',o],check=True)
p.link[p.link.index(str(REGS/'entry.o'))]=str(o)
s=(REGS/'gates.s').read_text();k='ngb_gate_indirect:\n';assert s.count(k)==1
s=s.replace(k,k+''' adrp x17,trial_variant
 ldr w17,[x17,:lo12:trial_variant]
 cbz w17,1f
 adr x17,ngb_indirect_slots
 sub x17,x16,x17
'''+f' mov x15,#{8*len(names)}\n'+''' cmp x17,x15
 b.hs 1f
 tst x17,#7
 b.ne 1f
 add x16,x16,#4
 br x16
1:
''')
s=s[:s.index('.section .note')]+'.p2align 3\nngb_indirect_slots:\n'+''.join(f'.global {n}\n.type {n},%function\n{n}: b slow_{n}\n b ngb_reg_{n}\n.size {n},.-{n}\n' for n in names)+'.section .note.GNU-stack,"",%progbits\n'
f=p.out/'slot.S';f.write_text(s);o=p.out/'slot.o';sp.run(['cc','-c',f,'-o',o],check=True);p.link[p.link.index(str(REGS/'gates.o'))]=str(o);p.link.insert(1,'-Wl,--strip-debug')
s=(RUNTIME/'scene/bridge.c').read_text();k='    ++scene_flips;';p.add('scene/bridge.c',s.replace(k,k+' extern void ngb_trial_flip(unsigned,unsigned);ngb_trial_flip(scene_flips,draws);'));p.finish()
