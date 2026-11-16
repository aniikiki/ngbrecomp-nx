/* Only enable on the guest thread, suppress nested probes and report outside the window. */
extern char __executable_start[];
void *__real_memcpy(void *, const void *, size_t);
void *__real_memmove(void *, const void *, size_t);
void *__real_memset(void *, int, size_t);
struct bulkrow {uintptr_t pc; unsigned op; uint64_t calls,bytes,ns,n,empty_ns,empty_n;};
static struct bulkrow bulk_rows[4096];
static _Thread_local unsigned bulk_on,bulk_busy;
static unsigned bulk_rng=0x56a191u;
static inline uint64_t bulk_clock(void){
 struct timespec t;if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t))abort();
 return (uint64_t)t.tv_sec*1000000000u+t.tv_nsec;
}
#define BULK_WRAP(name,type,opid) \
__attribute__((noinline)) void *__wrap_##name(void *dest,type arg,size_t bytes){ \
 if(!bulk_on || bulk_busy)return __real_##name(dest,arg,bytes); \
 bulk_busy=1;uintptr_t pc=(uintptr_t)__builtin_return_address(0)-(uintptr_t)__executable_start; \
 unsigned j=((pc>>2)*2654435761u+opid)&4095;struct bulkrow *r; \
 for(unsigned tries=0;;tries++,j=(j+1)&4095){if(tries==4096)abort();r=&bulk_rows[j];if(!r->calls || (r->pc==pc && r->op==opid))break;} \
 r->pc=pc;r->op=opid;r->calls++;r->bytes+=bytes; \
 bulk_rng=bulk_rng*1664525u+1013904223u;unsigned mode=bulk_rng>>27; \
 if(mode==1){uint64_t a=bulk_clock();uint64_t b=bulk_clock();r->empty_ns+=b-a;r->empty_n++;} \
 uint64_t start=mode==0?bulk_clock():0;void *v=__real_##name(dest,arg,bytes); \
 if(mode==0){r->ns+=bulk_clock()-start;r->n++;}bulk_busy=0;return v;}
BULK_WRAP(memcpy,const void *,0)
BULK_WRAP(memmove,const void *,1)
BULK_WRAP(memset,int,2)
void phase_flip(unsigned f){
 bulk_on=0;
 if(f==30||f==120)for(unsigned i=0;i<4096;i++){struct bulkrow *r=bulk_rows+i;if(!r->calls)continue;
 fprintf(stderr,"[BULK] %u %lx %u %llu %llu %llu %llu %llu %llu\n",f,(unsigned long)r->pc,r->op,(unsigned long long)r->calls,(unsigned long long)r->bytes,(unsigned long long)r->n,(unsigned long long)r->ns,(unsigned long long)r->empty_n,(unsigned long long)r->empty_ns);}
 if(!f||f==30)__real_memset(bulk_rows,0,sizeof bulk_rows);
 bulk_on=f<120;
}
