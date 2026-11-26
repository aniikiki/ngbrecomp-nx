"""Compare the native particle kernels with the instruction sequences from the local build."""
import os
from pathlib import Path
import re
import subprocess
import tempfile

here = Path(__file__).resolve().parent
root = here.parents[3]
gen = root / 'build/switch-runtime/gen'
runtime = root / 'packaging/switch/runtime'

def function(unit, address):
    source = (gen / f'recomp_{unit:04}.c').read_text()
    return re.search(r'void sub_' + address + r'\(void\)\n\{.*?\n}', source, re.S)[0]

reference = [function(unit, label) for unit, label in [
    (0,'000111F0'), (28,'00305CA0'), (28,'00305B90'), (28,'003058E0'), (28,'00305950'), (29,'00328232'),
    (15,'001BD9B0'), (15,'001BDD10')]]
unit = (gen / 'recomp_0009.c').read_text()
for name, begin, end in [
    ('move','loc_00124812: ;','    edi = MEM32(esi + 0x210);'),
    ('model_a','loc_00124ACF: ;','loc_00124AEF: ;'),
    ('model_b','loc_00124D9D: ;','loc_00124DBF: ;'),
    ('view','MEM16(ebx + 0xC) = LO16(edx);','loc_00125845: ;')]:
    start = unit.index(begin) + len(begin)
    reference.append('static void ref_' + name + '(uint32_t ebp) {\n' + unit[start:unit.index(end, start)] + '\n}')

with tempfile.TemporaryDirectory() as temp:
    out = Path(temp)
    (out / 'reference.inc').write_text('\n'.join(reference))
    subprocess.run([os.environ.get('CC','cc'), '-std=gnu11', '-O2', '-fno-strict-aliasing', '-ffp-contract=off',
                    '-I'+str(gen), '-I'+str(runtime), '-I'+str(out), here/'test_particle.c', '-o', out/'check'], check=True)
    subprocess.run([out/'check'], check=True)
