from pathlib import Path
import subprocess as sp, shlex
p = Path('/work/build/switch-runtime/core-perf')
p.mkdir(exist_ok=True)
b = p.parent / 'host'
w = p.parent / 'switch'
r = Path('/work/packaging/switch/runtime')
cs = sp.check_output(['ninja', '-t', 'commands', 'ngb-runtime-test'], cwd=b, text=True).splitlines()
link = shlex.split(cs[-1].split('&&')[1])
count = 0
for i, v in enumerate(link):
    if 'ngb_boot_code.dir/' in v and v.endswith('.c.o'):
        obj = w / v.replace('.c.o', '.o')
        assert obj.is_file(), obj
        link[i] = str(obj)
        count += 1
assert count == len(list((p.parent / 'gen').glob('recomp_*.c'))), 'partial Switch core'
for name in ['runtime_test.c', 'kernel_rtl.c', 'hooks.c']:
    c = next((shlex.split(x) for x in cs if x.endswith('/' + name)))
    old = c[c.index('-o') + 1]
    o = str(p / ('exact-' + name + '.o'))
    if name == 'runtime_test.c':
        t = (r / 'runtime.c').read_text().replace('RECOMP_TLS RecompRegs g_regs;', 'RecompRegs g_regs;')
        (p / 'exact-runtime.inc').write_text(t)
        q = p / 'exact-test.c'
        q.write_text((r / name).read_text().replace('#include "runtime.c"', '#include "exact-runtime.inc"'))
        c[-1] = str(q)
    c[c.index('-o') + 1] = o
    c[c.index('-MF') + 1] = o + '.d'
    c[1:1] = ['-I' + str(p.parent / 'gen'), '-include', str(r / 'switch_guest_regs.h')]
    sp.run(c, cwd=b, check=True)
    if old in link:
        link[link.index(old)] = o
    else:
        link.insert(1, o)
q = p / 'thread-pointer.S'
q.write_text('.text\n.global __aarch64_read_tp\n.type __aarch64_read_tp,%function\n__aarch64_read_tp:\n mrs x0,tpidr_el0\n ret\n.section .note.GNU-stack,"",@progbits\n')
o = str(p / 'thread-pointer.o')
sp.run(['cc', '-c', q, '-o', o], check=True)
link.insert(1, o)
link[link.index('-o') + 1] = str(p / 'exact')
sp.run(link, cwd=b, check=True)
import json
(p / 'exact-link.json').write_text(json.dumps(link))
