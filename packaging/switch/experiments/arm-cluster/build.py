"""Cluster the observed functions of one game phase in a single compiler
unit. Keep real memory, callbacks, all unobserved outgoing calls and normal
game ABI. Allow GCC to inline and specialize between original Xbox units."""
from pathlib import Path
import re,shlex,subprocess as sp,sys
root=Path('/work');p=root/'build/switch-runtime';w=p/'switch';d=p/'opt050/arm-cluster';d.mkdir(exist_ok=True)
names={l.split()[0] for l in (p/'opt050/actor-native/manifest.tsv').read_text().splitlines()}
fns={}
for f in sorted((p/'gen').glob('recomp_*.c')):
 for m in re.finditer(r'^void ((?:sub_|d3d_orig_)([0-9A-F]+))\(void\)\n\{.*?^\}',f.read_text(),re.M|re.S):
  if m[2] in names:fns[m[1]]=m[0]
assert len(fns)==len(names)
s='#define RECOMP_GENERATED_CODE\n#include "recomp_funcs.h"\n#include "arm_math.h"\n#include "matrix.h"\n#include <math.h>\n'
s+='\n'.join('static void grouped_'+k+'(void);' for k in fns)+'\n'
pat=re.compile(r'\b(?:sub_|d3d_orig_)[0-9A-F]+\b')
s+='\n'.join(pat.sub(lambda m:'grouped_'+m[0] if m[0] in fns else m[0],v).replace('void grouped_', 'static void grouped_',1) for v in fns.values())
s+='\nvoid grouped_actor_body(void){\n'
for name,ra,args in [('001482B0','147ed8','PUSH32(g_esp,g_edi);PUSH32(g_esp,g_esi);'),('00147F10','147ede','PUSH32(g_esp,g_esi);'),('00148120','147ee6','PUSH32(g_esp,g_esi);g_eax=g_edi;')]:
 if name=='001482B0':s+='g_esi=MEM32(g_esp+20);'
 s+=args+'PUSH32(g_esp,0x'+ra+');grouped_sub_'+name+'();\n'
s+='}\n'
cmd=next(shlex.split(x) for x in sp.check_output(['ninja','-t','commands','ngb-startup'],cwd=w,text=True).splitlines() if x.endswith('/recomp_0010.c'))
for flags,src,name in [(['-fno-semantic-interposition','-finline-functions'],s,'group'),([],None,'loop')]:
 if name=='loop':
  src=(p/'gen/recomp_0010.c').read_text();tag='loc_00147ECD: ;';assert src.count(tag)==1
  src='extern unsigned cluster_enabled(void);extern void grouped_actor_body(void);\n'+src.replace(tag,tag+' if(cluster_enabled()){grouped_actor_body();goto loc_00147EE6;}')
 f=d/(name+'.c');f.write_text(src);c=cmd.copy();o=str(d/(name+'.o'));c[c.index('-o')+1]=o;c[c.index('-MF')+1]=o+'.d';c[-1]=str(f);c[1:1]=flags+['-I'+str(root/'packaging/switch/runtime'),'-g0'];sp.run(c,cwd=w,check=True)
print('grouped',len(fns),'original functions')
