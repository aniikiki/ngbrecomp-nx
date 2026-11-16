"""Link the *packaged* Switch game objects to the offline host services."""
from pathlib import Path
import shlex
import subprocess as sp
import json
import sys

base=Path('/work/build/switch-runtime')
core=base/'core-perf'
work=base/'native-regs'
host=base/'host'
runtime=Path('/work/packaging/switch/runtime')
link=json.loads((core/'exact-link.json').read_text())
clip='--rigid-clip' in sys.argv
stack='--stack' in sys.argv
driver=work/('stack-driver.c' if stack else 'host-driver.c')
rt=(runtime/'runtime.c').read_text().replace('RECOMP_TLS RecompRegs g_regs;', 'RecompRegs g_regs;')
(work/'host-runtime.inc').write_text(rt)
driver.write_text((runtime/'runtime_test.c').read_text().replace('#include "runtime.c"', '#include "host-runtime.inc"'))
if stack:
    code=driver.read_text()
    tag='        if (flip == 30 || flip == 120 || flip == 1680'
    assert code.count(tag)==1
    driver.write_text('#define _GNU_SOURCE\n#include <errno.h>\n'+code.replace('void __real_ngb_kernel_log','#include "arm-stack.inc"\nvoid __real_ngb_kernel_log',1).replace(tag,'        arm_stack_window(flip);\n'+tag))
commands=sp.check_output(['ninja','-t','commands','ngb-runtime-test'],cwd=host,text=True).splitlines()
if clip:
    cc=next(shlex.split(l) for l in commands if l.endswith('/vk/backend.cpp'))
    obj=str(work/'backend-host-clip.o')
    cc[cc.index('-o')+1]=obj
    cc[cc.index('-MF')+1]=obj+'.d'
    cc.insert(1,'-DNGB_RIGID_CLIP')
    sp.run(cc,cwd=host,check=True)
    link.insert(1,obj)
cc=next(shlex.split(l) for l in commands if l.endswith('/runtime_test.c'))
if clip: cc.insert(1,'-DNGB_RIGID_CLIP')
obj=str(driver.with_suffix('.o'))
cc[cc.index('-o')+1]=obj
cc[cc.index('-MF')+1]=obj+'.d'
cc[1:1]=['-I'+str(runtime.parent/'perf'),'-I'+str(runtime),'-include',str(runtime/'switch_guest_regs.h'),'-DNGB_REGISTER_PACKAGE']
cc[-1]=str(driver)
sp.run(cc,cwd=host,check=True)
link[link.index(str(core/'exact-runtime_test.c.o'))]=obj
objects=sorted(work.glob('recomp_*.c.o'))
assert len(objects)==14
for obj in objects:
    i=next(i for i,v in enumerate(link) if v.endswith('/'+obj.name.replace('.c.o','.o')))
    link[i]=str(obj)
link[1:1]=[str(work/(n+'.o')) for n in ['entry','gates','checkpoint']]
link[link.index('-o')+1]=str(work/('clip-check' if clip else 'stack-check' if stack else 'host-check'))
sp.run(link,cwd=host,check=True)
