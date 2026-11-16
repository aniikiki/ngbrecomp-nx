extern int ngb_dev_memcmp(const void*,const void*,size_t);
extern void *ngb_dev_memcpy(void*,const void*,size_t),*ngb_dev_memmove(void*,const void*,size_t),*ngb_dev_memset(void*,int,size_t);
struct ms_site {uintptr_t pc; uint64_t calls,bytes,s,e,t,b; unsigned op;};
static struct ms_site ms_rows[4096];
static _Thread_local unsigned ms_on,ms_rng;
static uint64_t ms_now(void){struct timespec t;if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t))abort();return (uint64_t)t.tv_sec*1000000000+t.tv_nsec;}
static struct ms_site *ms_site(unsigned op,uintptr_t pc,size_t n){
 unsigned i=((pc>>2)^(pc>>14)^op)&4095;
 for(unsigned k=0;k<4096;k++,i=(i+1)&4095){struct ms_site *r=&ms_rows[i];if(!r->pc||(r->pc==pc&&r->op==op)){r->pc=pc;r->op=op;r->calls++;r->bytes+=n;return r;}}abort();
}
#define MS_CALL(op,type,call) do {if(!ms_on)return (call);struct ms_site*r=ms_site(op,(uintptr_t)__builtin_return_address(0),n);ms_rng=1664525u*ms_rng+1013904223u;unsigned sel=ms_rng>>26;if(sel==1){uint64_t ms_started=ms_now();__asm__ volatile("" ::: "memory");r->b+=ms_now()-ms_started;r->e++;}if(sel==0){uint64_t ms_started=ms_now();type y=(call);__asm__ volatile("" : "+r"(y) :: "memory");r->t+=ms_now()-ms_started;r->s++;return y;}return (call);}while(0)
int __wrap_memcmp(const void*a,const void*b,size_t n){MS_CALL(0,int,ngb_dev_memcmp(a,b,n));}
void *__wrap_memcpy(void*a,const void*b,size_t n){MS_CALL(1,void*,ngb_dev_memcpy(a,b,n));}
void *__wrap_memmove(void*a,const void*b,size_t n){MS_CALL(2,void*,ngb_dev_memmove(a,b,n));}
void *__wrap_memset(void*a,int v,size_t n){MS_CALL(3,void*,ngb_dev_memset(a,v,n));}
static void ms_boundary(unsigned f){
 if(f!=0&&f!=30&&f!=120)return;
 ms_on=0;
 if(f)for(unsigned i=0;i<4096;i++){const struct ms_site*r=ms_rows+i;if(r->pc)fprintf(stderr,"[TARGET_MEMORY] %u %u %lx %llu %llu %llu %llu %llu %llu\n",f,r->op,(unsigned long)r->pc,(unsigned long long)r->calls,(unsigned long long)r->bytes,(unsigned long long)r->s,(unsigned long long)r->e,(unsigned long long)r->t,(unsigned long long)r->b);}
 memset(ms_rows,0,sizeof ms_rows);ms_rng=577u;ms_on=f!=120;
}
