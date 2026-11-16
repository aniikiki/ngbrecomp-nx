"""Compare one deadline load vs mask and DPC loads on each private block poll.
Public entries and callbacks still see the exact ticket; deadline invalidation
is required whenever mask changes or a new DPC arrives."""
from pathlib import Path
import os
b=Path('/work/build/switch-runtime');d=b/'core-perf/opening-ticket';d.mkdir(exist_ok=True)
abi=Path('/work/packaging/switch/arm-registers');rt=abi.parent/'runtime'
s=(rt/'guest_memory.h').read_text()
a='    if (!(ticket & ngb_poll_mask) || ngb_pending_dpcs)\n        ngb_poll_due(ticket);'
assert s.count(a)==1
s=s.replace(a,'''    extern uint64_t ticket_deadline;
    if (__builtin_expect(ticket >= ticket_deadline || !ticket,0)) {
        unsigned mask=ngb_poll_mask, pending=ngb_pending_dpcs;
        ticket_deadline=pending ? 0 : (ticket | mask)+1;
        if (!(ticket & mask) || pending) ngb_poll_due(ticket);
    }''')
(d/'template.h').write_text(s)
os.environ['NGB_REG_OUT']=str(d)
s=(abi/'compile.py').read_text().replace("(r/'guest_memory.h').read_text()","(o/'template.h').read_text()")
exec(compile(s,'ticket-abi','exec'),{})
exec(compile((abi/'gates.py').read_text(),'ticket-gates','exec'),{})
for f in d.glob('recomp_*.s'):f.unlink()
