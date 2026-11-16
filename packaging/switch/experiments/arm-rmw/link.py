"""Use one short tail-branch at public entries for both arms. Local recursive
calls bound by the original compiler can still use the original implementation."""
from pathlib import Path
import subprocess as sp,sys,re,json
h=Path(__file__).resolve().parent;perf=h.parents[1]/'perf';sys.path.insert(0,str(perf))
from native_probe import *
p=NativeProbe('rmw');p.link=json.loads((p.core/'exact-link.json').read_text())
names=set((p.out/'names').read_text().splitlines());found=set()
for ix,old in enumerate(p.link.copy()):
 if not re.search(r'/recomp_\d+\.o$',old):continue
 syms=names&{l.split()[-1] for l in sp.check_output(['nm','-g','--defined-only',old],text=True).splitlines() if l.strip()}
 if not syms:continue
 found.update(syms);f=p.out/(Path(old).name+'.map');f.write_text(''.join(f'{n} base_{n}\n' for n in sorted(syms)));o=p.out/Path(old).name
 sp.run(['objcopy','--strip-debug','--redefine-syms='+str(f),old,o],check=True);p.link[ix]=str(o)
assert found==names
a=p.out/'select.S';a.write_text('.text\n'+''.join(f'.global {n}\n.type {n},%function\n{n}: adrp x16,trial_variant\n ldr w16,[x16,:lo12:trial_variant]\n cbz w16,1f\n b rmw_{n}\n1:b base_{n}\n' for n in sorted(names))+'.section .note.GNU-stack,"",%progbits\n')
o=p.out/'select.o';sp.run(['cc','-c',a,'-o',o],check=True);p.link[1:1]=[str(o),str(p.out/'fast.o'),'-Wl,--strip-debug']
driver=(p.core/'exact-test.c').read_text();tag='void __real_ngb_kernel_log';driver=driver.replace(tag,(perf/'trial.inc').read_text()+tag)
p.link[p.link.index(str(p.core/'exact-runtime_test.c.o'))]=p.compile('runtime_test.c',driver,['-include',str(RUNTIME/'switch_guest_regs.h'),'-I'+str(p.core),'-I'+str(RUNTIME)])
s=(RUNTIME/'scene/bridge.c').read_text();k='    ++scene_flips;';p.add('scene/bridge.c',s.replace(k,k+' extern void ngb_trial_flip(unsigned,unsigned);ngb_trial_flip(scene_flips,draws);'));p.finish()
