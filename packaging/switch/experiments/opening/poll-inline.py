"""Rebuild two O2 units, changing only whether the poll helper may be outlined."""
from pathlib import Path
p=Path(__file__).parent
s=(p/'page-hot-o3.py').read_text()
a=s.index('next_set=');b=s.index('parent=d.parent',a)
s=s[:a]+"d=(base/'core-perf/opening-poll-inline').resolve();d.mkdir(exist_ok=True)\n"+s[b:]
a=s.index('names=');b=s.index('\ns=s[:s.index',a)
s=s[:a]+"names=['recomp_0000.c','recomp_0028.c']"+s[b:]
a=s.index('s=s.replace(k," c[-1:');b=s.index('exec(compile(s,',a)
s=s[:a]+s[b:]
old='static inline void ngb_guest_block_poll(void)'
new='static inline __attribute__((always_inline)) void ngb_guest_block_poll(void)'
s=s.replace("(parent/'template.h').read_text()",f"(parent/'template.h').read_text().replace({old!r},{new!r})")
s=s.replace("(parent/'guest_memory.h').read_bytes()",f"(parent/'guest_memory.h').read_bytes().replace({old.encode()!r},{new.encode()!r})")
exec(compile(s,'poll-inline','exec'),{})
assert new in Path('build/switch-runtime/core-perf/opening-poll-inline/guest_memory.h').read_text()
