"""Check that every static game-to-XDK edge has a native handler and no old body remains."""
from pathlib import Path
import json
import re

root = Path(__file__).resolve().parents[4]
out = root / 'build/switch-runtime/core-perf/native-xdk'
table = (root / 'src/d3d/d3d_funcs.h').read_text()
native = (root / 'src/d3d/native_device.inc').read_text()
names = {int(a,16): n for a,n in re.findall(r'\{ 0x([\dA-F]+), "([^"]+)"', table)}
handled_names = set(re.findall(r'case D3DF_(\w+)\s*:', native))
handled_names.update(n for a,n in names.items() if a < 0x3c5c60)
handled = {a for a,n in names.items() if n in handled_names}
handled.update(int(a,16) for a in re.findall(r'case 0x([\da-f]+):', native.split('bool NativeHelper(')[1]))
removed = set(json.loads((out / 'intercepted.json').read_text()))
edges = {}
for file in (root / 'build/switch-runtime/gen').glob('recomp_*.c'):
    if not re.fullmatch(r'recomp_\d{4}\.c', file.name): continue
    for match in re.finditer(r'RECOMP_ENTRY\(0x([\dA-Fa-f]+)u\);(.*?)\n}', file.read_text(), re.S):
        caller = int(match[1],16)
        if caller in removed: continue
        for callee in re.findall(r'RECOMP_ABI_CALL\(0x([\dA-Fa-f]+)u', match[2]):
            address = int(callee,16)
            if address in removed: edges.setdefault(address,set()).add(caller)
assert not set(edges) - handled, [hex(x) for x in set(edges)-handled]
stubs = set()
for unit in (44,45):
    text = (out / f'recomp_{unit:04}.c').read_text()
    stubs.update(int(a,16) for a in re.findall(r'\{\s*ngb_d3d_native_entry\(0x([\da-f]+)u\);\s*}',text))
    entries = {int(a,16) for a in re.findall(r'RECOMP_ENTRY\(0x([\dA-Fa-f]+)u',text)}
    assert not entries & removed
assert stubs == removed and len(removed) == 226
report = {'removed_bodies': len(removed), 'native_handlers': len(handled),
          'static_external_targets': len(edges), 'static_external_edges': sum(map(len,edges.values())),
          'targets': {f'{a:08x}': {'name': names.get(a,'helper'), 'callers': [f'{c:08x}' for c in sorted(cs)]}
                      for a,cs in sorted(edges.items())},
          'limitation': 'Indirect calls are checked at runtime by strict native dispatch; untested content is not certified.'}
(out / 'coverage.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS:',len(removed),'old bodies removed;',len(edges),'static external targets handled')
