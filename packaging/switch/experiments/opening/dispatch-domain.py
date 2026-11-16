"""Select one of two disjoint address tables, retaining the generated call ABI."""
from pathlib import Path
import re
p=Path(__file__).parent
base=Path('build/switch-runtime')
rt=Path('packaging/switch/runtime/runtime.c').read_text()
assert 'recomp_lookup_manual(uint32_t va) { (void)va; return NULL; }' in rt
assert '#define THUNK_BASE 0xfe000000u' in rt
assert 'if (va < THUNK_BASE || ((va - THUNK_BASE) & 3u)) return NULL;' in rt
disp=(base/'gen/recomp_dispatch.c').read_text()
lo,n=[int(re.search(fr'g_flat_{key} = (0x[0-9a-fA-F]+)u;',disp)[1],16) for key in ('base','span')]
assert lo+n<=0xfe000000 and 'if (xbox_va - g_flat_base >= g_flat_span) return NULL;' in disp
hdr=(base/'gen/recomp_types.h').read_text()
old='recomp_lookup_manual(_va); '+chr(92)+'\n    if (!_fn) _fn = recomp_lookup(_va); '+chr(92)+'\n    if (!_fn) _fn = recomp_lookup_kernel(_va);'
new='(_va >= 0xfe000000u ? recomp_lookup_kernel(_va) : recomp_lookup(_va));'
defs=[]
for chunk in hdr.split('#define ')[1:]:
    macro=chunk.partition('} while(0)')[0]
    if old not in macro:continue
    name=macro.partition('(')[0]
    assert name in ('RECOMP_ICALL','RECOMP_ICALL_SAFE','RECOMP_ICALL_SAFE_AT','RECOMP_ITAIL')
    defs.append('#undef '+name+'\n#define '+macro.replace(old,new)+'} while(0)\n')
assert len(defs)==4
q=base/'core-perf/opening-dispatch-domain';q.mkdir(exist_ok=True)
(q/'dispatch-domain.h').write_text(''.join(defs))
s=(p/'page-hot-o3.py').read_text().replace("compact='--compact-loops' in sys.argv","compact=True").replace("d=d.parent/'opening-compact-loops'","d=d.parent/'opening-dispatch-domain'")
key="exec(compile(s,'page-o3','exec'),{})"
inject=""" src=(Path(c[-1])).read_text(); anchor='#include "recomp_funcs.h"';assert src.count(anchor)==1
 tmp=o/n;tmp.write_text(src.replace(anchor,anchor+'\\n#include "dispatch-domain.h"'))
 c[-1]=str(tmp)
 sp.run(c,cwd=w,check=True)
 tmp.unlink()"""
s=s.replace(key,"s=s.replace(' sp.run(c,cwd=w,check=True)',"+repr(inject)+")\n"+key)
exec(compile(s,'dispatch-domain','exec'),{})
