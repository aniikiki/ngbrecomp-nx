"""Compare the native material batch with the generated game's actual helpers.

The extracted reference stays in build/. Fake device calls model the existing
native XDK state/reference effects; randomized cases compare guest tables,
renderer state and the ordered resource bindings, including repeated materials.
"""
from pathlib import Path
import re
import subprocess

root = Path(__file__).resolve().parents[4]
out = root / 'build/switch-runtime/core-perf/native-material-test'
out.mkdir(parents=True, exist_ok=True)
source = (root / 'build/switch-runtime/gen/recomp_0028.c').read_text()
reference = []
for address in ('0030B7E0', '0030BA30', '0030D630'):
    match = re.search(r'void sub_' + address + r'\(void\)\n\{.*?\n}', source, re.S)
    assert match, address
    reference.append(match[0])
(out / 'reference.inc').write_text('\n'.join(reference))
command = ['clang++', '-std=c++17', '-O2', '-fno-strict-aliasing', '-ffp-contract=off',
           '-I' + str(out), '-I' + str(root / 'src/d3d'),
           str(Path(__file__).with_suffix('.cpp')), '-o', str(out / 'test')]
subprocess.run(command, check=True)
subprocess.run([out / 'test'], check=True)
