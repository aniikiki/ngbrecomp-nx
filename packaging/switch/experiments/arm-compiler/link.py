"""Select a compiler at entry to the hot graph. Rename only its definitions.
Common external entry stubs preserve C function pointer identity."""
from pathlib import Path
import subprocess as sp,sys,json
h=Path(__file__).resolve().parent;perf=h.parents[1]/'perf';sys.path.insert(0,str(perf));from native_probe import *
p=NativeProbe('compiler-pair');p.link=json.loads((p.core/'exact-link.json').read_text());objects=[];names=set()
for new in sorted((BASE/'compiler-study').glob('recomp_*.o')):
 i=next(i for i,v in enumerate(p.link) if v.endswith('/'+new.name));old=Path(p.link[i])
 def sy(obj):return {l.split()[-1] for l in sp.check_output(['nm','-g','--defined-only',obj],text=True).splitlines() if l.strip()}
 a,b=sy(old),sy(new);assert a==b,(a-b,b-a)
 assert not a&names;names.update(a)
 for obj,prefix in [(old,'control'),(new,'llvm')]:
  m=p.out/(prefix+new.name+'.map');m.write_text(''.join(f'{n} {prefix}_{n}\n' for n in sorted(a)))
  rep=p.out/(prefix+new.name);sp.run(['objcopy','--strip-debug','--redefine-syms='+str(m),obj,rep],check=True)
  if obj==old:p.link[i]=str(rep)
  else:objects.append(str(rep))
assert len(objects)==14
f=p.out/'select.S';f.write_text('.text\n'+''.join(f'.global {n}\n.type {n},%function\n{n}: adrp x16,trial_variant\n ldr w16,[x16,:lo12:trial_variant]\n cbz w16,1f\n b llvm_{n}\n1: b control_{n}\n' for n in sorted(names))+'.section .note.GNU-stack,"",%progbits\n')
o=p.out/'select.o';sp.run(['cc','-c',f,'-o',o],check=True);p.link[1:1]=[str(o),str(BASE/"compiler-study/newlib-fpclassify.o"),*objects,'-Wl,--strip-debug']
s=(p.core/'exact-test.c').read_text();k='void __real_ngb_kernel_log';p.link[p.link.index(str(p.core/'exact-runtime_test.c.o'))]=p.compile('runtime_test.c',s.replace(k,(perf/'trial.inc').read_text()+k),['-include',str(RUNTIME/'switch_guest_regs.h'),'-I'+str(p.core),'-I'+str(RUNTIME)])
s=(RUNTIME/'scene/bridge.c').read_text();k='    ++scene_flips;';p.add('scene/bridge.c',s.replace(k,k+' extern void ngb_trial_flip(unsigned,unsigned);ngb_trial_flip(scene_flips,draws);'));p.finish()
