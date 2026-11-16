"""Use the private ABI's existing x28 register-file pointer in generated C."""
from pathlib import Path
p=Path(__file__).parent
src=(p/'page-hot-o3.py').read_text()
k="d=d.parent/'opening-compact-loops'";assert src.count(k)==1
src=src.replace(k,"d=d.parent/'opening-reg-base'").replace("compact='--compact-loops' in sys.argv","compact=True")
k="exec(compile(s,'page-o3','exec'),{})";assert src.count(k)==1
extra='register RecompRegs *ngb_private_regs asm("x28");\n#undef RECOMP_REGS\n#define RECOMP_REGS (*ngb_private_regs)\n'
# Install only in these private units' forced header. Public entrances still set
# the pointer to g_regs; foreign exits retain the same AAPCS callee-saved x28.
src=src.replace(k,"s=s.replace('store=',"+repr("with header.open('a') as h:h.write("+repr(extra)+")\nstore=")+",1)\n"+k)
exec(compile(src,'reg-base-build','exec'),{})
