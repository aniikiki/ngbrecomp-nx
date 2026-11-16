"""Exercise public entry, private indirect and foreign fallback using the exact
generated bridge bodies, including preservation of host callee-saved registers."""
from pathlib import Path
import subprocess as sp,tempfile,runpy
p=Path(__file__).resolve().parent
base=Path('build/switch-runtime/core-perf/opening-full-guest')
s=(base/'entry.S').read_text();a=s.index('.section .text.xbe_entry_point,');b=s.index('.size xbe_entry_point,.-xbe_entry_point',a)
entry,gates=runpy.run_path(str(p/'compact-bridges.py'))['generate']('.text\n'+s[a:b]+'.size xbe_entry_point,.-xbe_entry_point\n',(base/'gates.s').read_text())
gates=gates[gates.index('ngb_gate_indirect:'):gates.index('.size ngb_gate_indirect,')]
driver="""
.text
.global ngb_reg_xbe_entry_point
ngb_reg_xbe_entry_point:
 add w19,w19,#17
 ret
foreign:
 ldr w8,[x28]
 add w8,w8,#31
 str w8,[x28]
 ret
.global run_checks
run_checks:
 stp x29,x30,[sp,-64]!
 stp x19,x20,[sp,16]
 stp x27,x28,[sp,32]
 adrp x28,g_regs
 add x28,x28,:lo12:g_regs
 mov w19,#71
 mov w8,#10
 str w8,[x28]
 bl xbe_entry_point
 cmp w19,#71
 b.ne 1f
 ldr w8,[x28]
 cmp w8,#27
 b.ne 1f
 adr x16,xbe_entry_point
 bl ngb_gate_indirect
 cmp w19,#88
 b.ne 1f
 ldr w8,[x28]
 cmp w8,#27
 b.ne 1f
 adr x16,foreign
 bl ngb_gate_indirect
 cmp w19,#119
 b.ne 1f
 ldr w8,[x28]
 cmp w8,#119
 b.ne 1f
 mov w0,#0
 b 2f
1: mov w0,#1
2: ldp x27,x28,[sp,32]
 ldp x19,x20,[sp,16]
 ldp x29,x30,[sp],64
 ret
.bss
.balign 8
.global ngb_fast_ram,ngb_fast_page_bytes,g_regs
ngb_fast_ram: .skip 8
ngb_fast_page_bytes: .skip 8
g_regs: .skip 128
"""
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);f=d/'check.S';o=d/'check';c=d/'main.c'
 f.write_text(entry+'\n.text\n'+gates+driver);c.write_text('int run_checks(void);int main(void){return run_checks();}')
 sp.run(['cc',f,c,'-o',o],check=True);sp.run([o],check=True)
print('AArch64 public entry, private indirect call and ordinary fallback passed')
