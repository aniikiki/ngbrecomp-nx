"""One full-page + alignment test for four-byte accesses, original checks on
miss. Keep the original 16-bit mapping table and register ABI."""
from pathlib import Path
import re,os
p=Path(__file__).resolve().parent
def edit(s):
 k='    if (__builtin_expect((address & 4095u) + bytes <= ngb_fast_page_bytes[address >> 12], 1))'
 assert s.count(k)==1
 return s.replace(k,'''    if (__builtin_constant_p(bytes) && bytes==4) {
        unsigned short len=ngb_fast_page_bytes[address>>12];
        if (__builtin_expect(((len ^ 4096u) | (address & 3u))==0,1) ||
            (address & 4095u)+4u<=len)
            return (uintptr_t)ngb_fast_ram+(address&0x7fffffffu);
        return ngb_guest_scalar_fallback(address,4);
    }
'''+k)
if __name__=='__main__':
 src=(p/'hot-image-span.py').read_text()
 a=src.index("k='    if (ngb_static_image_span");b=src.index("(d/'template.h')",a)
 src=(src[:a]+"s=edit(s)\n"+src[b:]).replace('opening-hot-image-span','opening-word-page')
 exec(compile(src,'word-page-build','exec'))
