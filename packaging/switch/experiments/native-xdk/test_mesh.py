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
callback = functions(['0030C2A0']).split('loc_0030C32E: ;\n', 1)[1]
(out / 'reference_callback.inc').write_text('static void reference_callback() {\n' + callback)
reference = functions(['0030BCA0','0030C240'])
# The control is the shipped 0.57.6 path, whose two material calls are native.
reference = reference.replace('RECOMP_ABI_CALL(0x0030B7E0u, sub_0030B7E0)', 'ngb_direct_material_fixed()')
reference = reference.replace('RECOMP_ABI_CALL(0x0030BA30u, sub_0030BA30)', 'ngb_direct_material_texture()')
(out / 'reference_mesh.inc').write_text(reference)
(out / 'reference_model.inc').write_text(functions(['003078B0','00307A10']))
adapter = (root / 'src/d3d/native_mesh.inc').read_text()
setters = ('simple', 'disable', 'unbind', 'modulate')
(out / 'mesh_setters.inc').write_text('\n'.join(
    re.search(r'extern "C" (void ngb_d3d_mesh_' + name + r'\([^)]*\) \{.*?\n})', adapter, re.S)[1]
    for name in setters))
ordered = functions(['00308D50', '0030D6D0'])
source = (root / 'build/switch-runtime/gen/recomp_0016.c').read_text()
ordered += '\n' + functions(['001CB260', '001CB510'])
source = (root / 'build/switch-runtime/gen/recomp_0029.c').read_text()
(out / 'reference_render_list.inc').write_text(ordered + '\n' + functions(['00318410']))
(out / 'reference_lights.inc').write_text(functions(['00318000','00317D10']))
subprocess.run(['clang++','-std=c++17','-O2','-g','-fno-strict-aliasing','-ffp-contract=off',
    '-fsanitize=address,undefined','-Wno-parentheses-equality','-I'+str(out),'-I'+str(root/'src/d3d'),
    str(Path(__file__).with_suffix('.cpp')),'-o',str(out/'test')],check=True)
subprocess.run([out/'test'],check=True)
subprocess.run(['clang++','-std=c++17','-O2','-DNGB_DIRECT3D','-fsanitize=address,undefined',
    '-I'+str(root/'src/d3d/compat'),str(Path(__file__).with_name('test_descriptor_pages.cpp')),
    '-o',str(out/'test-descriptor-pages')],check=True)
subprocess.run([out/'test-descriptor-pages'],check=True)
