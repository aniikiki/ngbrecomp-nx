"""Only the private game ABI can assume live RAM. Public wrappers check once.
The slow fallback retains the normal runtime checks; never assume dynamic globals
or an entire VM/stack arena stay mapped across a guest callback."""
from pathlib import Path
import os
base=Path('/work/build/switch-runtime');d=base/'core-perf/opening-image-literals';d.mkdir(exist_ok=True)
abi=Path('/work/packaging/switch/arm-registers');rt=abi.parent/'runtime'
s=(rt/'guest_memory.h').read_text()
a='ngb_static_image_span(address, bytes) && ngb_fast_ram'
assert s.count(a)==1
s=s.replace(a,'ngb_static_image_span(address, bytes)')
(d/'template.h').write_text(s)
os.environ['NGB_REG_OUT']=str(d)
s=(abi/'compile.py').read_text()
s=s.replace("(r/'guest_memory.h').read_text()","(o/'template.h').read_text()")
a='ldr x26,[x26,:lo12:ngb_fast_ram]\\n'
assert s.count(a)==1
s=s.replace(a,a+' cbnz x26,.+8\\n brk #0\\n')
exec(compile(s,'literal-abi','exec'),{})
exec(compile((abi/'gates.py').read_text(),'literal-gates','exec'),{})
for f in d.glob('recomp_*.s'):f.unlink()
