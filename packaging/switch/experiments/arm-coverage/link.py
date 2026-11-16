"""Keep the released fourteen units on both arms. For the additional units,
choose original public code or new private code at a shared call boundary."""
from pathlib import Path
import re,sys,subprocess as sp
h=Path(__file__).resolve().parent;perf=h.parents[1]/'perf';sys.path.insert(0,str(perf));from native_probe import *
p=NativeProbe('extended-abi');d=p.out
p.driver((perf/'trial.inc').read_text())
names=set(re.findall(r'^((?:sub_|d3d_orig_)\w+):$',(d/'entry.S').read_text(),re.M))
def renamed(obj,prefix,syms):
 f=d/(prefix+'-'+obj.name+'.map');f.write_text(''.join(f'{n} {prefix}_{n}\n' for n in sorted(syms)));o=d/(prefix+'-'+obj.name)
 sp.run(['objcopy','--strip-debug','--redefine-syms='+str(f),obj,o],check=True);return str(o)
for o in d.glob('recomp_*.c.o'):
 i=next(i for i,v in enumerate(p.link) if v.endswith('/'+o.name.replace('.c.o','.o')))
 orig=Path(p.link[i]);syms={l.split()[-1] for l in sp.check_output(['nm','-g','--defined-only',orig],text=True).splitlines() if l.strip()}
 assert syms<=names
 p.link[i]=renamed(orig,'base',syms);p.link.insert(1,str(o))
p.link.insert(1,renamed(d/'entry.o','fast',names))
# The existing private code sometimes reaches a new target through a gate.
# On the baseline arm retain the old register publication and public call.
old=(REGS/'gates.s').read_text()
s=(d/'all-gates.S').read_text()
def branch(m):
 name=m[1];k=f'ngb_gate_{name}:\n';a=old.index(k)+len(k);b=re.search(r'^\.(?:global|section|size) ',old[a:],re.M).start()+a
 return f'ngb_gate_{name}: adrp x16,trial_variant\n ldr w16,[x16,:lo12:trial_variant]\n cbnz w16,ngb_reg_{name}\n'+old[a:b].replace(' bl '+name+'\n',' bl base_'+name+'\n').rstrip()
s=re.sub(r'^ngb_gate_(\w+): b ngb_reg_\1$',branch,s,flags=re.M)
a=d/'select.S';a.write_text(s+'\n.text\n'+''.join(f'.global {n}\n.type {n},%function\n{n}: adrp x16,trial_variant\n ldr w16,[x16,:lo12:trial_variant]\n cbnz w16,fast_{n}\n b base_{n}\n' for n in sorted(names)))
# Conditional branch range is only 1 MiB. Always use a long plain branch.
a.write_text(re.sub(r' cbnz w16,(\w+)\n',r' cbz w16,1f\n b \1\n1:\n',a.read_text()))
o=d/'select.o';sp.run(['cc','-c',a,'-o',o],check=True);p.link[p.link.index(str(REGS/'gates.o'))]=str(o)
p.link.insert(1,'-Wl,--strip-debug')
s=(RUNTIME/'scene/bridge.c').read_text();k='    ++scene_flips;';p.add('scene/bridge.c',s.replace(k,k+' extern void ngb_trial_flip(unsigned,unsigned);ngb_trial_flip(scene_flips,draws);'));p.finish()
