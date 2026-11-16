"""Use the native ABI optimizer with finalized bare-metal profiles. Original profiles untouched."""
import os,struct,subprocess
from pathlib import Path
base=Path('/work/build/switch-runtime');abi=Path('/work/packaging/switch/arm-registers')
src=base/'core-perf/opening-register-pgo/profiles';out=base/'core-perf/opening-merged-pgo'
out.mkdir(exist_ok=True);units=[2,16,28];names=[f'recomp_{i:04}.c' for i in units]
for name in names:
 f,=src.rglob(name+'.native.gcda');dst=out/'profiles'/f.relative_to(src)
 dst.parent.mkdir(parents=True,exist_ok=True)
 # Always regenerate the private copy from one run; merging over a prior copy doubles counts.
 dst.unlink(missing_ok=True)
 raw=f.read_bytes();fname=os.fsencode(dst)+bytes(1)
 subprocess.run(['/opt/devkitpro/devkitA64/bin/aarch64-none-elf-gcov-tool','merge-stream'],input=struct.pack('<I',0x6763666e)+raw[4:8]+struct.pack('<I',len(fname))+fname+raw,check=True)
 assert dst.is_file()
os.environ.update(NGB_REG_OUT=str(out),NGB_REG_PROFILE='use')
s=(abi/'compile.py').read_text().split("f=o/'entry.S'")[0]
s=s.replace('ex.map(build,units)','ex.map(build,'+repr(names)+')')
# Keep identical compilation-unit and forced-header names to training, even
# for static inline helpers whose GCC profile identities depend on those names.
trained=src.parent
assert all((trained/h).exists() for h in ['regs.h','guest_memory.h'])
inject=""" trained=Path('/work/build/switch-runtime/core-perf/opening-register-pgo')
 assert all((trained/h).read_bytes()==(o/h).read_bytes() for h in ['regs.h','guest_memory.h'])
 c[c.index('-I'+str(o))]='-I'+str(trained)
 c[c.index(str(header))]=str(trained/'regs.h')
 tmpasm=trained/(n+'.native.s')
 assert not tmpasm.exists()
 c[c.index('-o')+1]=str(tmpasm)
 try:
  sp.run(c,cwd=w,check=True)
  tmpasm.replace(o/(n+'.native.s'))
 finally:tmpasm.unlink(missing_ok=True)
"""
s=s.replace(' sp.run(c,cwd=w,check=True)\n',inject)
exec(compile(s,'verified-pgo','exec'),{})
exec(compile((abi/'gates.py').read_text(),'pgo-gates','exec'),{})
for f in out.glob('recomp_*.s'):f.unlink()
