"""Build the RNG observer for unit 37 under the original 14-unit ABI."""
from pathlib import Path
import os,subprocess as sp,runpy,sys
p=Path(__file__).resolve().parent
root=Path('/work/build/switch-runtime')
abi=p.parents[1]/'arm-registers'
d=root/'core-perf/opening-rng-original';d.mkdir(exist_ok=True)
os.environ['NGB_REG_OUT']=str(d)
name='recomp_0037.c'
s=(abi/'compile.py').read_text().split("f=o/'entry.S'")[0]
k=' sp.run(c,cwd=w,check=True)'
assert s.count(k)==1 and s.count('ex.map(build,units)')==1
s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\n"+k).replace('ex.map(build,units)',"ex.map(build,['recomp_0037.c'])")
src=d/name
try:
 if '--audit-only' not in sys.argv:
  src.write_text(runpy.run_path(str(p/'rng-correspondence.py'))['transform']((root/'gen'/name).read_text(),37))
  exec(compile(s,'original-guest','exec'),{})
  exec(compile((abi/'gates.py').read_text(),'original-gates','exec'),{})
 nm='/opt/devkitpro/devkitA64/bin/aarch64-none-elf-nm'
 def names(obj,flag):
  return {l.split()[-1] for l in sp.check_output([nm,'-g',flag,obj],text=True).splitlines() if l.split()}
 a=root/'native-regs'/(name+'.o');b=d/(name+'.o')
 assert names(a,'--defined-only')==names(b,'--defined-only')
 assert names(b,'-u')-names(a,'-u')=={'rr_fixed','rr_set','rr_observe'}
 assert (d/'guest_memory.h').read_bytes()==(a.parent/'guest_memory.h').read_bytes()
 prefix=(a.parent/'regs.h').read_text()
 checks=''.join(f'_Static_assert(__builtin_offsetof(RecompRegs,r_{reg})=={j*4},"register file layout");\n' for j,reg in enumerate(['eax','ecx','edx','esp','ebx','esi','edi']))
 assert (d/'regs.h').read_text() in (prefix,prefix+checks)
 print('verified baseline unit symbols, header parity and observer externals')
finally:
 src.unlink(missing_ok=True)
 for f in d.glob('*.s'):f.unlink()
