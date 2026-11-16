"""Generate both code and state access through the existing private x28 register."""
from pathlib import Path
import sys
here=Path(__file__).resolve().parent;abi=here.parents[1]/'arm-registers'
base=Path('/work/build/switch-runtime');d=base/'opt050/state';d.mkdir(exist_ok=True)
s=(abi/'compile.py').read_text().replace("o=w.parent/'native-regs'","o=w.parent/'opt050/state'")
i=s.index('store=');s=s[:i]+"with header.open('a') as h:h.write("+repr((here/'state.h').read_text())+")\n"+s[i:]
i=s.index("(o/'guest_memory.h').write_text(mem)")
s=s[:i]+'''tag='void ngb_poll_due(uint64_t ticket);'
mem=mem.replace(tag,tag+'\\n#define ngb_guest_polls (NG_STATE->polls)\\n#define ngb_poll_mask (NG_STATE->mask)\\n#define ngb_pending_dpcs (NG_STATE->pending)')
'''+s[i:]
# GCC cannot declare a fixed global register after another declaration has used it.
# All generated TUs have no prior executable code before forced regs.h.
i=s.index(" sp.run(c,cwd=w,check=True)")
s=s[:i]+''' body=(w.parent/'gen'/n).read_text()
 tag='#include "recomp_funcs.h"'
 assert body.count(tag)==1
 body=body.replace(tag,tag+'\\n#include "entry-inline.h"')
 src=o/n;src.write_text(body);c[-1]=str(src)
'''+s[i:]
(d/'entry-inline.h').write_text('''
#undef RECOMP_ENTRY
#define RECOMP_ENTRY(A) do { \\
 if ((A)==0x17a010u || (A)==0x31dc50u || (A)==0x3cc310u || __builtin_expect(NG_STATE->entries<48,0)) ngb_checkpoint(A); \\
 else { uint64_t e=NG_STATE->entries++; NG_STATE->va=(A);NG_STATE->recent[e&31]=(A);ngb_guest_block_poll(); } \\
}while(0)
''')
exec(compile(s,'arm-state-cross','exec'),{'__name__':'__main__'})
s=(abi/'gates.py').read_text().replace('/switch-runtime/native-regs','/switch-runtime/opt050/state')
exec(compile(s,'arm-state-gates','exec'),{'__name__':'__main__'})
