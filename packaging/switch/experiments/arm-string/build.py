"""Compile just affected guest functions; no generated game code retained in
the source tree. Keep the public ABI, original poll points and XDK hooks."""
from pathlib import Path
import re,shlex,subprocess as sp,sys

p=Path('/work/build/switch-runtime');w=p/'switch';meter='--meter' in sys.argv;d=p/'core-perf'/('fill-meter' if meter else 'arm-string');d.mkdir(exist_ok=True)
ccs=sp.check_output(['ninja','-t','commands','ngb-startup'],cwd=w,text=True).splitlines()
src='#define RECOMP_GENERATED_CODE\n#include "recomp_funcs.h"\n#include "matrix.h"\n#include "direct/output.h"\n#include "nv2a_boot.h"\n#include "services.h"\n#include "ohci_boot.h"\n#include "arm_math.h"\n#include <math.h>\n';src+=Path(__file__).with_name('fill.h').read_text();src+='extern void ngb_fill_meter(unsigned,unsigned,unsigned,int);\n';names=[];total=0
for n in range(47):
 name=f'recomp_{n:04}.c';s=(p/'gen'/name).read_text()
 for m in re.finditer(r'^void (sub_[0-9A-F]+)\(void\)\n\{.*?^\}',s,re.M|re.S):
  base=m[0];k='{ uint32_t _i; int32_t _st = RECOMP_DF_STEP(4); for (_i = 0; _i < ecx; _i++) MEM32(edi + _i*_st) = eax; edi += ecx * _st; }'
  alt=base.replace(k,'if(ngb_stos_fast(edi,ecx,eax,g_df)){edi+=ecx*RECOMP_DF_STEP(4);}else '+k)
  if meter:alt=base.replace(k,'ngb_fill_meter(0x'+m[1][4:]+'u,ecx,eax,g_df);'+k)
  if alt!=base:
   total+=base.count(k);names.append(m[1]);src+=alt.replace('void '+m[1]+'(', 'void stos_'+m[1]+'(',1)+'\n'
assert len(names)==len(set(names));(d/'names').write_text('\n'.join(names));f=d/'fast.c';f.write_text(src)
cmd=next(shlex.split(x) for x in ccs if x.endswith('/recomp_0016.c'));o=str(d/'fast.o');cmd[cmd.index('-o')+1]=o;cmd[cmd.index('-MF')+1]=o+'.d';cmd[-1]=str(f);cmd[1:1]=['-g0'];cmd.insert(-1,'-g0');sp.run(cmd,cwd=w,check=True)
print(len(names),'functions;',total,'REP fill sites')
