"""For byte loads/stores any offset fits in an ordinary full page.
The current map uses exactly zero or 4096; require 4096 to keep partial
pages on the checked fallback. No alignment assumptions or new map."""
from pathlib import Path
import re,os
p=Path(__file__).resolve().parent
def edit(s):
 k='    if (__builtin_expect((address & 4095u) + bytes'
 assert s.count(k)==1
 return s.replace(k,'''    if (__builtin_constant_p(bytes) && bytes==1) {
        if (__builtin_expect(ngb_fast_page_bytes[address>>12]==4096,1))
            return (uintptr_t)ngb_fast_ram+(address&0x7fffffffu);
        return ngb_guest_scalar_fallback(address,1);
    }
'''+k)
if __name__=='__main__':
 src=(p/'hot-image-span.py').read_text()
 a=src.index("k='    if (ngb_static_image_span");b=src.index("(d/'template.h')",a)
 src=(src[:a]+"s=edit(s)\n"+src[b:]).replace('opening-hot-image-span','opening-byte-page')
 exec(compile(src,'byte-page-build','exec'))
