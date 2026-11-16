from pathlib import Path
import sys,json,subprocess as sp
h=Path(__file__).resolve().parent;sys.path.insert(0,str(h.parents[1]/'perf'));from native_probe import *
p=NativeProbe('actor-cluster');d=BASE/'opt050/arm-cluster';link=json.loads((p.core/'exact-link.json').read_text());p.link=link
# Reference and optimized paths share the original public register ABI.
link[link.index(next(v for v in link if v.endswith('/recomp_0010.o')))]=str(d/'loop.o')
link.insert(1,str(d/'group.o'))
s=(p.core/'exact-test.c').read_text();tag='void __real_ngb_kernel_log';s=s.replace(tag,(h.parents[1]/'perf/trial.inc').read_text()+'unsigned cluster_enabled(void){return trial_variant;}\n'+tag)
obj=p.compile('runtime_test.c',s,['-include',str(RUNTIME/'switch_guest_regs.h'),'-I'+str(p.core),'-I'+str(RUNTIME)]);link[link.index(str(p.core/'exact-runtime_test.c.o'))]=obj
s=(RUNTIME/'scene/bridge.c').read_text();k='    ++scene_flips;';p.add('scene/bridge.c',s.replace(k,k+' extern void ngb_trial_flip(unsigned,unsigned);ngb_trial_flip(scene_flips,draws);'));p.finish()
