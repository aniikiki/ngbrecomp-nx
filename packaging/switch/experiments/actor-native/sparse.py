"""Portable Switch worker: only copy pages actually encountered, independently
for each worker. No virtual-address aliases, signals or Linux fork needed.
Caller must keep source pages immutable until job completion; fallback on cap."""
from pathlib import Path
from readonly import loads
here=Path(__file__).resolve().parent
s=(here/'build.py').read_text().replace("d=p/'opt050/actor-native'","d=p/'opt050/actor-sparse'")
s=s.replace('unsigned pc,error; union { jmp_buf escape; unsigned char reserved[1024]; } unwind;', '''unsigned pc,error,used;uint16_t *index;unsigned char *slots;uint16_t *touched; union { jmp_buf escape; unsigned char reserved[1024]; } unwind;''')
a=s.index('static inline void *ngb_ram_span');b=s.index('#define ngb_guest_pointer',a)
s=s[:a]+'''static inline void actor_bail(unsigned e){ac.error=e;longjmp(ac.unwind.escape,1);}
static inline void *actor_page(uint32_t a,size_t n){
 unsigned off=a&0x7fffffffu,pg=off>>12;
 if(pg>=32768 || n>4096u-(off&4095u) || (off&4095u)+n>ac.pages[a>>12])actor_bail(a);
 unsigned slot=ac.index[pg];
 if(!slot){if(ac.used>=512)actor_bail(0xf0000001u);slot=++ac.used;ac.index[pg]=slot;ac.touched[slot-1]=pg;
   __builtin_memcpy(ac.slots+(slot-1)*4096,ac.ram+pg*4096,4096);}
 return ac.slots+(slot-1)*4096+(off&4095u);
}
static inline const void *actor_read_page(uint32_t a,size_t n){
 unsigned off=a&0x7fffffffu,pg=off>>12;
 if(pg>=32768 || n>4096u-(off&4095u) || (off&4095u)+n>ac.pages[a>>12])actor_bail(a);
 unsigned slot=ac.index[pg];return slot?ac.slots+(slot-1)*4096+(off&4095u):ac.ram+off;
}
#define ACTOR_R8(a) ((uint8_t)*(const volatile uint8_t*)actor_read_page(a,1))
#define ACTOR_R16(a) ((uint16_t)*(const volatile uint16_t*)actor_read_page(a,2))
#define ACTOR_R32(a) ((uint32_t)*(const volatile uint32_t*)actor_read_page(a,4))
#define ACTOR_RF(a) ((float)*(const volatile float*)actor_read_page(a,4))
#define ACTOR_RD(a) ((double)*(const volatile double*)actor_read_page(a,8))
static inline void *ngb_ram_span(uint32_t a,size_t n){
 if(n>4096u-(a&4095u)||(a&4095u)+n>ac.pages[a>>12])return 0;
 return actor_page(a,n);}
static inline void *ngb_guest_vector_page(uint32_t a){return ngb_ram_span(a,16);}
static inline uintptr_t ngb_guest_scalar(uint32_t a,size_t n){return (uintptr_t)actor_page(a,n);}
'''+s[b:]
tag="code=prefix+"
i=s.index(tag)
s=s[:i]+'''types=(d/'recomp_types.h').read_text().replace('ngb_fast_ram + (addr & 0x7fffffffu)','actor_page(addr,16)')
assert types.count('actor_page(addr,16)')==2
types=types.replace('__builtin_memcpy(&r, actor_page(addr,16)', '__builtin_memcpy(&r, actor_read_page(addr,16)')
(d/'recomp_types.h').write_text(types)
scan=(r/'scan_tags.inc').read_text()
# The scan count is already limited to this page. Check that full range
# before handing a read-only pointer to the scan loop.
(d/'scan_tags.inc').write_text(scan.replace('ngb_fast_ram + (esi & 0x7fffffffu)','(const unsigned char*)actor_read_page(esi,count*4)'))
'''+s[i:]
s=s.replace('#include \"matrix.h\"', '#include \"worker_matrix.h\"')
p=Path('/work/build/switch-runtime/opt050/actor-sparse/worker_matrix.h');p.parent.mkdir(parents=True,exist_ok=True)
p.write_text(Path('/work/packaging/switch/runtime/matrix.h').read_text().replace('ngb_guest_vector_page(left)','actor_read_page(left,64)').replace('ngb_guest_vector_page(right)','actor_read_page(right,64)'))
tag=" srcs[va]=src";s=s.replace(tag,''' src=loads(src).replace('ngb_fast_ram + (first & 0x7fffffffu)','actor_page(first,4)')
 if 'ngb_fast_ram' in src:raise ValueError('unaudited raw game RAM access '+va)
'''+tag)
s=s.replace('unsigned ngb_actor_native(void *result,unsigned char *ram,const uint16_t *pages,uint64_t *polls,uint64_t *entries){','''unsigned ngb_actor_sparse(void *result,unsigned char *ram,const uint16_t *pages,uint64_t *polls,uint64_t *entries,uint16_t *index,unsigned char *slots,uint16_t *touched,unsigned *used){
 ac.index=index;ac.slots=slots;ac.touched=touched;ac.used=*used;''').replace('if(setjmp(ac.unwind.escape))return ac.error?ac.error:~0u;', 'if(setjmp(ac.unwind.escape)){*used=ac.used;return ac.error?ac.error:~0u;}').replace('*entries=ac.entries;return 0;', '*entries=ac.entries;*used=ac.used;return 0;')
# The online diagnostic learns read/write pages on its first traversal. An
# absent page in a subsequent snapshot must fault before it can be read.
if '--footprint' in __import__('sys').argv:
 s=s.replace('unsigned pc,error,used;', 'unsigned pc,error,used;uint8_t *foot;')
 s=s.replace('unsigned slot=ac.index[pg];', 'ac.foot[pg]=1;unsigned slot=ac.index[pg];')
 s=s.replace('uint16_t *touched,unsigned *used){','uint16_t *touched,unsigned *used,uint8_t *foot){ac.foot=foot;')
 s=s.replace("o=str(d/'actor.o')","o=str(d/'footprint.o')")
exec(compile(s,'sparse-actor-build','exec'))
