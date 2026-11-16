from pathlib import Path
import subprocess as sp, json, sys
p = Path('/work/build/switch-runtime/core-perf')
p.mkdir(exist_ok=True)
b = p.parent / 'host'
mode = sys.argv[1]
l = json.loads((p / 'exact-link.json').read_text())
for n in json.loads((p / 'pgo-files.json').read_text()):
    k = next((i for i, v in enumerate(l) if v.endswith('/' + n.replace('.c', '.o'))))
    l[k] = str(p / 'pgo' / (n + '.o'))
if mode == 'train':
    sp.run(['cc', '-O2', '-c', Path(__file__).with_name('emit.c'), '-o', p / 'emit.o'], check=True)
    l.insert(1, str(p / 'emit.o'))
    l.append(str(p / 'cross-gcov.a'))
l[l.index('-o') + 1] = str(p / mode)
sp.run(l, cwd=b, check=True)
