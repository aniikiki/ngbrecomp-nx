from pathlib import Path
import subprocess as sp, concurrent.futures, shlex, sys, shutil, json
p = Path('/work/build/switch-runtime/core-perf')
p.mkdir(exist_ok=True)
b = p.parent / 'switch'
o = p / 'pgo'
o.mkdir(exist_ok=True)
cs = sp.check_output(['ninja', '-t', 'commands', 'ngb-startup'], cwd=b, text=True).splitlines()
mode = sys.argv[1]
assert mode in ('train', 'guided')
files = ['recomp_%04d.c' % v for v in (0, 1, 2, 3, 9, 10, 11, 14, 16, 27, 28, 29, 37, 44)]

def compile(n):
    c = next((shlex.split(x) for x in cs if x.endswith('/' + n)))
    q = o / (n + '.o')
    c[c.index('-o') + 1] = str(q)
    c[c.index('-MF') + 1] = str(q) + '.d'
    c = c[:-2] + ['-g0', '-fno-semantic-interposition', '-O3'] + (['-fprofile-arcs', '-fprofile-info-section=ngb_training', '-fprofile-update=single'] if mode == 'train' else ['-fprofile-use', '-fno-profile-values', '-fprofile-partial-training', '-Werror=missing-profile', '-Werror=coverage-mismatch']) + c[-2:]
    sp.run(c, check=True, cwd=b)
with concurrent.futures.ThreadPoolExecutor(5) as ex:
    list(ex.map(compile, files))
if mode == 'train':
    cc = '/opt/devkitpro/devkitA64/bin/aarch64-none-elf-gcc'
    lib = sp.check_output([cc, '-print-file-name=libgcov.a'], text=True).strip()
    shutil.copy(lib, p / 'cross-gcov.a')
(p / 'pgo-files.json').write_text(json.dumps(files))
