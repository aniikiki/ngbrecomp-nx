"""One contiguous proof from 0x8000 up to the live first hole. Admit aligned words only."""
from pathlib import Path
def vm(s):
 k='uint32_t opening_end4[1u<<20];'
 assert s.count(k)==1
 s=s.replace(k,k+'''
__attribute__((visibility("hidden"))) uint32_t lp_words;
static void lp_extend(void){
 unsigned p=8+(lp_words>>10);
 while(p<NGB_VM_END/4096 && opening_end4[p]==(p<<12)+4093u)++p;
 lp_words=(p-8)<<10;
}
''')
 k='    memset(pages, 0, sizeof(pages));';assert s.count(k)==1
 s=s.replace(k,k+' lp_words=0; if(memory)lp_extend();')
 k='    *base = address;';assert s.count(k)==1
 s=s.replace(k,'    if ((flags&COMMIT) && first+NGB_VM_BEGIN/PAGE<=8+(lp_words>>10) && first+NGB_VM_BEGIN/PAGE+count>8+(lp_words>>10)) lp_extend();\n'+k)
 k='    *base = NGB_VM_BEGIN + first * PAGE;';assert s.count(k)==1
 return s.replace(k,'    if(first+NGB_VM_BEGIN/PAGE<8+(lp_words>>10))lp_words=(first+NGB_VM_BEGIN/PAGE-8)<<10;\n'+k)
def header(s):
 k='static inline __attribute__((always_inline)) uintptr_t ngb_guest_scalar(uint32_t address, size_t bytes)'
 assert s.count(k)==1
 s=s.replace(k,'''extern __attribute__((visibility("hidden"))) uint32_t lp_words;
static __attribute__((noinline,noclone,cold)) uintptr_t low_word_miss(uint32_t a){
 if(a<reg_ends[a>>12])return (uintptr_t)ngb_fast_ram+(a&0x7fffffffu);
 return ngb_guest_scalar_fallback(a,4);
}
'''+k)
 k='    if (__builtin_constant_p(bytes) && bytes>=1 && bytes<=4)';assert s.count(k)==1
 return s.replace(k,'''    if(__builtin_constant_p(bytes) && bytes==4){
        uint32_t off=address-0x8000u;
        if(__builtin_expect(((off>>2)|(off<<30))<lp_words,1))return (uintptr_t)ngb_fast_ram+address;
        return low_word_miss(address);
    }
'''+k)
if __name__=='__main__':
 p=Path(__file__).parent
 s=(p/'page-hot-o3.py').read_text().replace("compact='--compact-loops' in sys.argv","compact=True").replace("d=d.parent/'opening-compact-loops'","d=d.parent/'opening-low-words'")
 for k in ["(parent/'template.h').read_text()","(parent/'guest_memory.h').read_text()"]:
  assert s.count(k)==1;s=s.replace(k,'header('+k+')')
 exec(compile(s,'low-words','exec'),{'header':header})
