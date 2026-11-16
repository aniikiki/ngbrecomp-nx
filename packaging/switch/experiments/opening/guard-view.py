from pathlib import Path
import runpy,re
p=Path(__file__).parent
def allocator():
 s=(p/'alias-host.c').read_text().replace('void *__wrap_calloc', (p/'guard-view.inc').read_text()+'\nvoid *__wrap_calloc').replace(' close(fd);',' guard_setup(fd);close(fd);').replace('if(area && p==area){','if(area && p==area){if(munmap(guard_area,G_LENGTH))abort();guard_area=guard_active=NULL;')
 return s
def mapping(s):
 # Notify immediately after every per-page publication. Reset outside the
 # opening is harmless; abort if a full table reset occurs during observation.
 k='memset(opening_end4,0,sizeof opening_end4);'
 s=s.replace(k,'if(guard_active){__builtin_abort();}\n    '+k)
 s,n=re.subn(r'(opening_end4\[([^\]]+)\]=ngb_fast_page_bytes[^;]+;)',r'\1 guard_update(\2);',s)
 assert n in (1,3),n
 return 'extern void guard_update(unsigned);extern unsigned char *guard_active;\n'+s
def transform(s,u):
 k='#include "recomp_funcs.h"';assert s.count(k)==1
 return s.replace(k,k+'''
extern unsigned char *guard_active;
static inline __attribute__((always_inline)) uintptr_t gv_word(uint32_t a){
 if(ngb_static_image_span(a,4)) return ngb_guest_scalar(a,4);
 if(guard_active && !(a&3u))return (uintptr_t)guard_active+a;
 return ngb_guest_scalar(a,4);
}
#undef MEM32
#define MEM32(a) (*(volatile uint32_t*)gv_word((uint32_t)(a)))
''')
if __name__=='__main__':runpy.run_path(str(p/'model-copy.py'))['build']('guard-view',[(True,[2,10,16,26,39])],transform)
