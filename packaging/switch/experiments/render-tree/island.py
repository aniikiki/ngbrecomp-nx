"""Compile the four main render callbacks and their shared mesh-submit chain
as one private ARM region. Original HLE mirror, Xbox device body, polling and
guest ABI all remain; ordinary public calls are the fallback on every exit."""
from pathlib import Path
import shlex,subprocess as sp,re,sys
h=Path(__file__).resolve().parent;w=Path('/work');base=w/'build/switch-runtime';d=base/'core-perf/render-island';d.mkdir(exist_ok=True);perf=h.parents[1]/'perf'
roots='001CB260 001CB3B0 001CB510 001CB550'.split()
if sys.argv[1]=='cross':
 names=set(roots+'003078B0 00307B80 00307A10 0030BCA0 0030C1A0 0030B7E0 0030BA30 0030C240 0030C2A0 0030C370 00308130 0030B020 00317DC0 00317D10 00318000'.split())
 srcs={}
 for f in (base/'gen').glob('recomp_*.c'):
  for m in re.finditer(r'^void sub_([A-F0-9]+)\(void\)\n\{.*?^\}',f.read_text(),re.M|re.S):
   if m[1] in names:srcs[m[1]]=m[0]
 assert names==set(srcs)
 def rename(m):return 'region_'+m[1] if m[1] in names else m[0]
 src='#define RECOMP_GENERATED_CODE\n#include "recomp_funcs.h"\n#include "arm_math.h"\n#include "direct/output.h"\n#include "matrix.h"\n'
 for n in sorted(names):src+=('' if n in roots else 'static ')+'void region_'+n+'(void);\n'
 for n,s in srcs.items():src+=('' if n in roots else 'static ')+re.sub(r'\bsub_([0-9A-F]+)\b',rename,s)+'\n'
 f=d/'region.c';f.write_text(src);o=str(d/'region.o')
 c=next(shlex.split(x) for x in sp.check_output(['ninja','-t','commands','ngb-startup'],cwd=base/'switch',text=True).splitlines() if x.endswith('/recomp_0028.c'))
 c[c.index('-o')+1]=o;c[c.index('-MF')+1]=o+'.d';c[-1]=str(f);c[-1:-1]=['-g0','-finline-functions','-fno-semantic-interposition'];sp.run(c,cwd=base/'switch',check=True)
 print('region',len(names),'functions')
else:
 import json
 sys.path.insert(0,str(perf));from native_probe import *
 p=NativeProbe('render-island');p.link=json.loads((p.core/'exact-link.json').read_text())
 old=next(v for v in p.link if v.endswith('/recomp_0016.o'));o=p.out/'orig.o'
 sp.run(['objcopy','--strip-debug',*[f'--redefine-sym=sub_{v}=base_{v}' for v in roots],old,o],check=True);p.link[p.link.index(old)]=str(o)
 src='.text\n'+''.join(f'.global sub_{v}\n.type sub_{v},%function\nsub_{v}: adrp x16,trial_variant\n ldr w16,[x16,:lo12:trial_variant]\n cbz w16,1f\n b region_{v}\n1:b base_{v}\n' for v in roots)+'.section .note.GNU-stack,"",%progbits\n'
 f=d/'select.S';f.write_text(src);o=d/'select.o';sp.run(['cc','-c',f,'-o',o],check=True);p.link[1:1]=[str(o),str(d/'region.o'),'-Wl,--strip-debug']
 s=(p.core/'exact-test.c').read_text();k='void __real_ngb_kernel_log';s=s.replace(k,(perf/'trial.inc').read_text()+k)
 p.link[p.link.index(str(p.core/'exact-runtime_test.c.o'))]=p.compile('runtime_test.c',s,['-include',str(RUNTIME/'switch_guest_regs.h'),'-I'+str(p.core),'-I'+str(RUNTIME)])
 s=(RUNTIME/'scene/bridge.c').read_text();k='    ++scene_flips;';p.add('scene/bridge.c',s.replace(k,k+' extern void ngb_trial_flip(unsigned,unsigned);ngb_trial_flip(scene_flips,draws);'));p.finish()
