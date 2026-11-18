"""Compare the indexed state path with the archived, shipped table scans."""
from pathlib import Path
import re
import struct
import subprocess

root = Path(__file__).resolve().parents[4]
baseline = root/'build/switch-runtime/reports/native-model-0.57.7/reference-sources/src/d3d'
out = root/'build/switch-runtime/core-perf/native-simple-test'
out.mkdir(parents=True, exist_ok=True)
source = (baseline/'native_device.inc').read_text()
reference = re.search(r'void NativeSimple\(.*?\n}', source, re.S)[0].replace('NativeSimple(', 'NativeSimpleReference(')
source = (baseline/'hle.cpp').read_text().split('void SyncDeferred() {',1)[1]
start = source.index('    const auto* methods =')
end = source.index('    for (int s = 0;',start)
reference += '\nvoid NativeSyncSimpleReference() {\n' + source[start:end] + '}\n'
(out/'reference_simple.inc').write_text(reference)
data = (root/'game_files/default.xbe').read_bytes()
base = struct.unpack_from('<I',data,0x104)[0]
count, table = struct.unpack_from('<II',data,0x11c)
for i in range(count):
    flags, va, size, raw, raw_size = struct.unpack_from('<IIIII',data,table-base+i*56)
    if va <= 0x3e9278 and 0x3e9278 + 92*4 <= va + raw_size:
        assert not (flags & 1), 'simple encoding table must be read-only'
        values = struct.unpack_from('<92I',data,raw+0x3e9278-va)
        break
else:
    raise AssertionError('simple encoding table not in file-backed XBE sections')
(out/'real-table.inc').write_text(','.join(hex(v) for v in values))
subprocess.run(['clang++','-std=c++17','-O2','-g','-fsanitize=address,undefined',
    '-I'+str(out),'-I'+str(root/'src/d3d'),str(Path(__file__).with_suffix('.cpp')),
    '-o',str(out/'test')],check=True)
subprocess.run([out/'test'],check=True)
