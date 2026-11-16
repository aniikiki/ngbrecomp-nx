"""Build the offline guest-thread PC sampler against the exact Switch objects."""
from pathlib import Path
import subprocess as sp
import shlex
import json
import sys

root = Path('/work/build/switch-runtime')
core = root / 'core-perf'
build = root / 'host'
calls = '--libcalls' in sys.argv
out = core / ('libcalls' if calls else 'sample-pc')
out.mkdir(exist_ok=True)
driver = (core / 'exact-test.c').read_text()
point = '        if (flip == 30 || flip == 120 || flip == 1680'
assert driver.count(point) == 1
src = out / 'sample.c'
src.write_text('#define _GNU_SOURCE\n' + driver.replace('void __real_ngb_kernel_log',
    ('void libcall_window(unsigned);' if calls else '#include "sample-pc.inc"')+'\nvoid __real_ngb_kernel_log', 1).replace(point, ('        libcall_window(flip);\n' if calls else '        sample_window(flip);\n') + point))
cmds = sp.check_output(['ninja', '-t', 'commands', 'ngb-runtime-test'], cwd=build, text=True)
cc = next(shlex.split(x) for x in cmds.splitlines() if x.endswith('/runtime_test.c'))
obj = str(out / 'sample.o')
cc[cc.index('-o')+1] = obj
cc[cc.index('-MF')+1] = obj+'.d'
cc[-1] = str(src)
cc[1:1] = ['-I'+str(core), '-I'+str(Path(__file__).resolve().parent), '-include',
           '/work/packaging/switch/runtime/switch_guest_regs.h']
sp.run(cc, cwd=build, check=True)
link = json.loads((core/'exact-link.json').read_text())
link[link.index(str(core/'exact-runtime_test.c.o'))] = obj
link[link.index('-o')+1] = str(out/'replay')
if calls:
    hook = out / 'libcalls.o'
    sp.run(['cc','-O2','-c',Path(__file__).with_name('libcalls.c'),'-o',hook],check=True)
    link[1:1] = [str(hook),'-Wl,--wrap=memcmp','-Wl,--wrap=clock_gettime']
sp.run(link, cwd=build, check=True)
