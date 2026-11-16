"""Carry Xbox XMM0 in AArch64 v16 across translated calls. Every real service,
including libc, sees its RAM image, and reloads 128 bits after returning.
Public slot entry and slow checkpoint use identical publication barriers."""
import os,re,subprocess as sp
from pathlib import Path
root=Path('/work');base=root/'build/switch-runtime';abi=root/'packaging/switch/arm-registers'
d=base/'core-perf/opening-vector-registers';d.mkdir(exist_ok=True);os.environ['NGB_REG_OUT']=str(d)
# XMM0 is at 120 (8-byte aligned); ldur/stur handle this non-scaled offset.
qsave='\tstur q16,[x28,#120]\n';qload='\tldur q16,[x28,#120]\n'
store='\tstp w19, w20, [x28]\n\tstp w21, w22, [x28, 8]\n\tstp w23, w24, [x28, 16]\n\tstr w25, [x28, 24]\n'
load=store.replace('stp','ldp').replace('str','ldr')
header='\n_Static_assert(__builtin_offsetof(RecompRegs,r_xmm0)==120,"XMM0 offset");\nregister RecompXmm open_xmm0 asm("v16");\n#undef g_xmm0\n#define g_xmm0 open_xmm0\n'
def checked(s,a,b):
 assert s.count(a)==1,a
 return s.replace(a,b)
rt=abi.parent/'runtime';h=(rt/'matrix.h').read_text()
h=checked(h,'memcpy(&g_xmm0, &term2, 16);','{RecompXmm t;memcpy(&t,&term2,16);g_xmm0=t;}')
(d/'matrix.h').write_text(h)
s=(abi/'compile.py').read_text()
s=checked(s,'store=','with header.open("a") as h:h.write('+repr(header)+')\nstore=')
# Narrow the vector ABI to code compiled in these units: local helpers are
# allowed to mutate the bank, while external libc services must spill it.
s=checked(s,' sp.run(c,cwd=w,check=True)',' c.insert(-1,"-ffixed-v16")\n sp.run(c,cwd=w,check=True)')
# pure helpers are still ordinary machine ABI calls, except internal helpers
# compiled in this unit (recognized and unwrapped later by gates.py).
s=checked(s,'or t in pure or t in (\'XMM_MEM\',\'XMM_STORE\')','or t in ()')
exec(compile(s,'vector-abi','exec'),{})
cc='/opt/devkitpro/devkitA64/bin/aarch64-none-elf-gcc'
s=(abi/'gates.py').read_text()
s=checked(s," dst=out/(obj.stem+'.gated.s')"," s=s.replace(store,store+"+repr(qsave)+").replace(load,load+"+repr(qload)+")\n dst=out/(obj.stem+'.gated.s')")
s=checked(s,"sp.run([cc,'-c',a,", "a.write_text(a.read_text().replace(store,store+"+repr(qsave)+").replace(load,load+"+repr(qload)+"))\nsp.run([cc,'-c',a,")
exec(compile(s,'vector-gates','exec'),{})
for name,raw in [('entry',(d/'entry.S').read_text()),('checkpoint',(abi/'checkpoint.S').read_text())]:
 assert store in raw and load in raw
 f=d/(name+'.S');f.write_text(raw.replace(store,store+qsave).replace(load,load+qload))
 sp.run([cc,'-c',f,'-o',d/(name+'.o')],check=True)
for f in d.glob('recomp_*.s'):f.unlink()
