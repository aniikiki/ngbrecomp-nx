#define SITE ((uintptr_t)__builtin_extract_return_addr(__builtin_return_address(0)))
#define ACCESS(N) \
void __tsan_read##N(void*p){observe(p,N,0,SITE);} void __tsan_write##N(void*p){observe(p,N,1,SITE);} \
void __tsan_read_write##N(void*p){observe(p,N,0,SITE);observe(p,N,1,SITE);} \
void __tsan_unaligned_read##N(void*p){observe(p,N,0,SITE);} void __tsan_unaligned_write##N(void*p){observe(p,N,1,SITE);}
ACCESS(1) ACCESS(2) ACCESS(4) ACCESS(8) ACCESS(16)
void __tsan_init(void){}

void __tsan_read_range(void *p,unsigned long n){if(n<=RAM)observe(p,(unsigned)n,0,SITE);}
void __tsan_write_range(void *p,unsigned long n){if(n<=RAM)observe(p,(unsigned)n,1,SITE);}
// Match the compiler-rt ABI. Preserve the real atomic operations in the
// instrumented game. Outside guest RAM observe() discards the access.
uint32_t __tsan_atomic32_fetch_add(volatile uint32_t *p,uint32_t v,int order){
    observe((void*)p,4,0,SITE);observe((void*)p,4,1,SITE);return __atomic_fetch_add(p,v,order);
}
int __tsan_atomic32_compare_exchange_strong(volatile uint32_t *p,uint32_t *expected,uint32_t desired,int success,int failure){
    observe((void*)p,4,0,SITE);observe((void*)p,4,1,SITE);return __atomic_compare_exchange_n(p,expected,desired,0,success,failure);
}
