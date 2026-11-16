"""Compile just affected guest functions; no generated game code retained in
the source tree. Keep the public ABI, original poll points and XDK hooks."""
from pathlib import Path
import re,shlex,subprocess as sp
from rewrite import fuse
p=Path('/work/build/switch-runtime');w=p/'switch';d=p/'core-perf/simd-spans';d.mkdir(exist_ok=True)
ccs=sp.check_output(['ninja','-t','commands','ngb-startup'],cwd=w,text=True).splitlines()
src='#define RECOMP_GENERATED_CODE\n#include "recomp_funcs.h"\n#include "matrix.h"\n#include "arm_math.h"\n#include <math.h>\n';src+="#define NG_LOAD(p) ({RecompXmm z_;__builtin_memcpy(&z_,(p),16);z_;})\n#define NG_STORE(p,v) do{RecompXmm z_=(v);__builtin_memcpy((p),&z_,16);}while(0)\n";names=[];total=0
for n in (0,1,2,3,9,10,11,14,16,27,28,29,37,44):
 name=f'recomp_{n:04}.c';s=(p/'gen'/name).read_text()
 for m in re.finditer(r'^void (sub_[0-9A-F]+)\(void\)\n\{.*?^\}',s,re.M|re.S):
  base=m[0];alt,nrun=fuse(base)
  if alt!=base:
   total+=nrun;names.append(m[1]);src+=alt.replace('void '+m[1]+'(', 'void simd_'+m[1]+'(',1)+'\n'
assert len(names)==len(set(names));(d/'names').write_text('\n'.join(names));f=d/'fast.c';f.write_text(src)
cmd=next(shlex.split(x) for x in ccs if x.endswith('/recomp_0016.c'));o=str(d/'fast.o');cmd[cmd.index('-o')+1]=o;cmd[cmd.index('-MF')+1]=o+'.d';cmd[-1]=str(f);cmd[1:1]=['-g0'];cmd.insert(-1,'-g0');sp.run(cmd,cwd=w,check=True)
print(len(names),'functions;',total,'verified SIMD spans')
