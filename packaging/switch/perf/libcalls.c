/* Linux replay only. Calls from render threads aren't charged to the game. */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
extern char __executable_start[];
static _Thread_local int live;
enum { N = 8192 };
static struct bucket { uintptr_t pc; size_t size; unsigned op,count,equal; } table[N];
static void hit(uintptr_t pc, size_t size, unsigned op,int equal)
{
    uintptr_t key=pc-(uintptr_t)__executable_start;
    unsigned i=((key>>2)^(size*2654435761u)^op)&(N-1);
    for(unsigned j=0;j<N;j++,i=(i+1)&(N-1)){
        struct bucket *b=&table[i];
        if(!b->count || (b->pc==key && b->size==size && b->op==op)){
            b->pc=key;b->size=size;b->op=op;b->count++;b->equal+=equal;return;
        }
    }
    abort();
}
int __real_memcmp(const void*,const void*,size_t);
int __wrap_memcmp(const void*a,const void*b,size_t n){
    int r=__real_memcmp(a,b,n);
    if(live)hit((uintptr_t)__builtin_return_address(0),n,1,r==0);
    return r;
}
int __real_clock_gettime(clockid_t,struct timespec*);
int __wrap_clock_gettime(clockid_t id,struct timespec*t){
    if(live)hit((uintptr_t)__builtin_return_address(0),(unsigned)id,2,0);
    return __real_clock_gettime(id,t);
}
void libcall_window(unsigned flip){
    if(flip==1800)live=1;
    if(flip==1920){live=0;for(unsigned i=0;i<N;i++){
        struct bucket *b=&table[i];if(b->count)fprintf(stderr,"[LIBCALL] %u %lx %zu %u %u\n",
            b->op,(unsigned long)b->pc,b->size,b->count,b->equal);
    }}
}
