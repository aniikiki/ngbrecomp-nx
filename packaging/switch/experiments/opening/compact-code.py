"""Measure compact A57 code in the same 14 private ABI units. No changes to
game work, shader output, guest page permissions or scheduling frequency."""
from pathlib import Path
import os
base=Path('/work/build/switch-runtime');abi=Path('/work/packaging/switch/arm-registers')
d=base/'core-perf/opening-compact-code';d.mkdir(exist_ok=True);os.environ['NGB_REG_OUT']=str(d)
s=(abi/'compile.py').read_text()
k=' sp.run(c,cwd=w,check=True)'
assert s.count(k)==1
s=s.replace(k," c[-1:-1]=['-Os','-fno-partial-inlining','-fno-ipa-icf']\n"+k)
exec(compile(s,'compact-abi','exec'),{})
exec(compile((abi/'gates.py').read_text(),'compact-gates','exec'),{})
for f in d.glob('recomp_*.s'):f.unlink()
