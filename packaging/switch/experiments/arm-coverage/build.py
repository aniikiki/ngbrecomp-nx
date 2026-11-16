"""Extend the existing private ABI without compiling the original 14 units
again. Redirect their existing exact sync gates only for newly internal
targets. The old package, sources, and objects are never overwritten."""
from pathlib import Path
import re,subprocess as sp
p=Path('/work/build/switch-runtime');abi=Path('/work/packaging/switch/arm-registers');d=p/'core-perf/extended-abi';d.mkdir(exist_ok=True)
extra=[13,5,31,8,45,15,26,33]
s=(abi/'compile.py').read_text().replace("o=w.parent/'native-regs'","o=w.parent/'core-perf/extended-abi'").replace('ns=[0,1,2,3,9,10,11,14,16,27,28,29,37,44]','ns='+repr(extra))
# The new code can call existing internal entries. Generate public entry
# symbols solely for the new units; the prior 3500 wrappers stay intact.
tag='header=o/'
s=s.replace(tag,'''new_symbols=symbols.copy()
symbols.update(__import__('re').findall(r'^((?:sub_|d3d_orig_)[0-9A-F]+):$',(w.parent/'native-regs/entry.S').read_text(),__import__('re').M))
'''+tag).replace('sorted(symbols))+','sorted(new_symbols))+')
if '--merge-only' not in __import__('sys').argv:exec(compile(s,'additional-private-units','exec'),{})
s=(abi/'gates.py').read_text().replace('/switch-runtime/native-regs','/switch-runtime/core-perf/extended-abi')
exec(compile(s,'additional-private-gates','exec'),{})
old=(p/'native-regs/gates.s').read_text();new=(d/'gates.s').read_text();entries=set(re.findall(r'^((?:sub_|d3d_orig_)\w+):$',(d/'entry.S').read_text(),re.M))
pat=re.compile(r'^\.global ngb_gate_(\w+)\n.*?(?=^\.global |^\.section |\Z)',re.M|re.S)
names=set()
def redirect(m):
 name=m[1];names.add(name)
 if name not in entries:return m[0]
 return f'.global ngb_gate_{name}\n.type ngb_gate_{name},%function\nngb_gate_{name}: b ngb_reg_{name}\n.size ngb_gate_{name},.-ngb_gate_{name}'
old=pat.sub(lambda m:redirect(m).rstrip()+'\n',old);out=old[:old.index('.section .note')]+''.join(m[0]+'\n' for m in pat.finditer(new) if m[1] not in names)+'.section .note.GNU-stack,"",%progbits\n'
f=d/'all-gates.S';f.write_text(out);sp.run(['/opt/devkitpro/devkitA64/bin/aarch64-none-elf-gcc','-c',f,'-o',d/'all-gates.o'],check=True)
print('added',len(entries),'private entries; previous exit gates now direct:',len(names&entries))
