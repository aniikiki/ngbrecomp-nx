"""Differential test against the actual generated mesh submission and commands."""
from pathlib import Path
import re
import subprocess

root = Path(__file__).resolve().parents[4]
out = root / 'build/switch-runtime/core-perf/native-mesh-test'
out.mkdir(parents=True, exist_ok=True)
source = (root / 'build/switch-runtime/gen/recomp_0028.c').read_text()
def functions(addresses):
    return '\n'.join(re.search(r'void sub_' + a + r'\(void\)\n\{.*?\n}', source, re.S)[0] for a in addresses)
(out / 'reference.inc').write_text(functions(['0030B7E0','0030BA30','0030D630']))
reference = functions(['0030BCA0','0030C240'])
# The control is the shipped 0.57.6 path, whose two material calls are native.
reference = reference.replace('RECOMP_ABI_CALL(0x0030B7E0u, sub_0030B7E0)', 'ngb_direct_material_fixed()')
reference = reference.replace('RECOMP_ABI_CALL(0x0030BA30u, sub_0030BA30)', 'ngb_direct_material_texture()')
(out / 'reference_mesh.inc').write_text(reference)
(out / 'reference_model.inc').write_text(functions(['003078B0','00307A10']))
subprocess.run(['clang++','-std=c++17','-O2','-g','-fno-strict-aliasing','-ffp-contract=off',
    '-fsanitize=address,undefined','-Wno-parentheses-equality','-I'+str(out),'-I'+str(root/'src/d3d'),
    str(Path(__file__).with_suffix('.cpp')),'-o',str(out/'test')],check=True)
subprocess.run([out/'test'],check=True)
