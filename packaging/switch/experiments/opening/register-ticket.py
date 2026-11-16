"""Keep the Xbox poll counter in x28 throughout private game code. Synchronize it
at *all* exits, including register-file bridges, slow checkpoint callbacks and
public re-entry. Pure C math/libc must preserve x28 by AAPCS."""
from pathlib import Path
import os,subprocess as sp
base=Path('/work/build/switch-runtime');abi=Path('/work/packaging/switch/arm-registers')
d=base/'core-perf/opening-register-ticket';d.mkdir(exist_ok=True);os.environ['NGB_REG_OUT']=str(d)
# x16 may hold an indirect-call target. x0..x7 may hold arguments/return; use
# x17 only on a real foreign boundary, where it is call-clobbered.
publish='\tadrp x17, ngb_guest_polls\n\tstr x28,[x17,:lo12:ngb_guest_polls]\n\tadrp x17,g_regs\n\tadd x17,x17,:lo12:g_regs\n'
reload='\tadrp x17,ngb_guest_polls\n\tldr x28,[x17,:lo12:ngb_guest_polls]\n'
greg='\tstp w19, w20, [x28]\n\tstp w21, w22, [x28, 8]\n\tstp w23, w24, [x28, 16]\n\tstr w25, [x28, 24]\n'
gload=greg.replace('stp','ldp').replace('str','ldr')
store=publish+greg.replace('x28','x17')
load='\tadrp x17,g_regs\n\tadd x17,x17,:lo12:g_regs\n'+gload.replace('x28','x17')+reload
s=(abi/'compile.py').read_text()
k="(o/'guest_memory.h').write_text(mem)";assert s.count(k)==1
decl='void ngb_poll_due(uint64_t ticket);'
ins='register uint64_t private_ticket asm("x28");\n#define ngb_guest_polls private_ticket\n'+decl
s=s.replace(k,f'mem=mem.replace({decl!r},{ins!r})\n'+k)
# First fold the shared gates with their standard marker; transform the remaining
# inline foreign boundaries after gate selection, before final assembly.
exec(compile(s,'ticket-register','exec'),{})
s=(abi/'gates.py').read_text()
k=" dst=out/(obj.stem+'.gated.s')";assert s.count(k)==1
s=s.replace(k," s=s.replace(store,"+repr(store)+").replace(load,"+repr(load)+")\n"+k)
k="sp.run([cc,'-c',a,'-o',out/'gates.o']";assert s.count(k)==1
s=s.replace(k,"a.write_text(a.read_text().replace(store,"+repr(store)+").replace(load,"+repr(load)+"))\n"+k)
exec(compile(s,'ticket-register-gates','exec'),{})
cc='/opt/devkitpro/devkitA64/bin/aarch64-none-elf-gcc'
f=d/'entry.S';s=f.read_text()
k=' adrp x28,g_regs\n add x28,x28,:lo12:g_regs\n'
assert s.count(k)==3500
s=s.replace(k,'').replace(gload,load).replace(greg,store)
f.write_text(s);sp.run([cc,'-c',f,'-o',d/'entry.o'],check=True)
f=d/'checkpoint.S';s=(abi/'checkpoint.S').read_text()
a=s.index('\tadrp\tx1, ngb_guest_polls');z=s.index('\tadrp\tx1, ngb_poll_mask',a)
s=s[:a]+'\tadd x28,x28,1\n\tmov x0,x28\n'+s[z:]
assert s.count(greg)==2 and s.count(gload)==2
f.write_text(s.replace(greg,store).replace(gload,load));sp.run([cc,'-c',f,'-o',d/'checkpoint.o'],check=True)
# Sanity: no stale private register-file accesses survived the transformation.
for f in d.glob('*.gated.s'):
 s=f.read_text()
 assert '[x28,' not in s and '[x28]' not in s, f
for f in d.glob('recomp_*.s'):f.unlink()
