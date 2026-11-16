"""Use the census to select four units; classify a dynamic scalar VA before
its page lookup. The whole scalar must be inside immutable ordinary-RAM
*mapping* (contents remain volatile). Includes pointers, not just table indices."""
from pathlib import Path
import re,os
d=Path('/work/build/switch-runtime/core-perf/opening-hot-image-span');d.mkdir(exist_ok=True)
abi=Path('/work/packaging/switch/arm-registers')
s=(abi.parent/'runtime/guest_memory.h').read_text()
k='    if (ngb_static_image_span(address, bytes) && ngb_fast_ram)'
assert s.count(k)==1
s=s.replace(k,'''    const unsigned lo=(NGB_TICK_COUNT|4095u)+1u;
    if (!__builtin_constant_p(address) && __builtin_constant_p(bytes) && bytes && bytes<=16 &&
        (uint32_t)(address-lo) <= NGB_VM_BEGIN-lo-bytes && ngb_fast_ram)
        return (uintptr_t)ngb_fast_ram+address;
'''+k)
(d/'template.h').write_text(s);os.environ['NGB_REG_OUT']=str(d)
s=(abi/'compile.py').read_text().replace("(r/'guest_memory.h').read_text()","(o/'template.h').read_text()")
s=re.sub(r'^ns=\[[\d,]+\]$', 'ns=list(range(47))',s,flags=re.M)
num=r'(?:sub_|d3d_orig_)[0-9A-F]+'
s=s.replace(num,'(?:'+num+'|xbe_entry_point)')
s=s[:s.index("f=o/'entry.S'")].replace('ex.map(build,units)','ex.map(build,'+repr([f'recomp_{i:04}.c' for i in (2,16,26,39)])+')')
exec(compile(s,'hot-image-span','exec'),{})
exec(compile((abi/'gates.py').read_text(),'hot-image-gates','exec'),{})
for f in d.glob('recomp_*.s'):f.unlink()
