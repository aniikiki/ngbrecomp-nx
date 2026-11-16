// Only the guest thread is in scope. Register PC and bytes for out-of-line
// calls; measure a second pass with clocks disabled to expose probe overhead.
static _Thread_local int cmp_active;
static int cmp_clock;
static struct {uintptr_t pc;uint64_t calls,bytes,ns,equal;} cmp_slots[2048];
int __real_memcmp(const void*,const void*,size_t);
static inline uint64_t cmp_ns(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec*1000000000ull+t.tv_nsec;}
int __wrap_memcmp(const void*a,const void*b,size_t n){
 if(!cmp_active)return __real_memcmp(a,b,n);
 uintptr_t pc=(uintptr_t)__builtin_return_address(0);
 unsigned i=(pc>>2)%2048;
 unsigned first=i;
 while(cmp_slots[i].pc && cmp_slots[i].pc!=pc){i=(i+1)%2048;if(i==first)abort();}
 cmp_slots[i].pc=pc;cmp_slots[i].calls++;cmp_slots[i].bytes+=n;
 uint64_t t=cmp_clock?cmp_ns():0;
 int r=__real_memcmp(a,b,n);
 if(cmp_clock)cmp_slots[i].ns+=cmp_ns()-t;
 cmp_slots[i].equal+=!r;return r;
}
void cmp_boundary(unsigned f){
 cmp_active=f>=30 && f<120;cmp_clock=getenv("NGB_COMPARE_CLOCK")!=NULL;
 if(f==120)for(unsigned i=0;i<2048;i++)if(cmp_slots[i].pc)fprintf(stderr,"[COMPARE] %lx %lu %lu %lu %lu\n",(unsigned long)cmp_slots[i].pc,cmp_slots[i].calls,cmp_slots[i].bytes,cmp_slots[i].ns,cmp_slots[i].equal);
}
