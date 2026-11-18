/* Run the actual Switch logger lifecycle with pthread-backed thread services.
 * Hold the output FILE lock: all three producers must still complete. */
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>
typedef uint64_t u64;
typedef int Result;
typedef struct { pthread_t id; void (*entry)(void*); void* arg; unsigned handle; } Thread;
#define R_SUCCEEDED(x) ((x)==0)
static void* thread_entry(void* p) { Thread* t=p; t->entry(t->arg); return NULL; }
static Result threadCreate(Thread* t,void(*entry)(void*),void* arg,void* stack,size_t size,int priority,int core) {
    (void)stack;(void)size;(void)priority;(void)core;t->entry=entry;t->arg=arg;return 0;
}
static Result threadStart(Thread* t) { return pthread_create(&t->id,NULL,thread_entry,t); }
static Result threadWaitForExit(Thread* t) { return pthread_join(t->id,NULL); }
static void threadClose(Thread* t) { (void)t; }
static Thread* threadGetSelf(void) { return NULL; }
static Result thread_ticks(unsigned handle,u64* value) { (void)handle;*value=0;return 1; }
static uint64_t armTicksToNs(uint64_t t) { return t; }
static void svcSleepThread(uint64_t ns) { struct timespec t={ns/1000000000,ns%1000000000};nanosleep(&t,NULL); }
uint64_t ngb_elapsed_ns(void) { struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec*1000000000ull+t.tv_nsec; }
#define __SWITCH__ 1
#define NGB_NATIVE_DIAG 1
#include "combat_perf.inc"

static atomic_uint completed;
static void* produce(void* argument) {
    unsigned ring=(unsigned)(uintptr_t)argument;
    const unsigned kinds[]={'G','R','D'},columns[]={13,32,5};
    for(unsigned i=0;i<600;++i) {
        uint64_t values[32];for(unsigned j=0;j<32;++j)values[j]=1000000*ring+100*i+j;
        ngb_combat_row(kinds[ring],values,columns[ring]);
    }
    atomic_fetch_add(&completed,1);return NULL;
}
int main(int argc,char** argv) {
    assert(argc==2 && combat_open(argv[1]));
    flockfile(cp_file);
    assert(combat_start_writer());
    pthread_t producers[3];
    for(unsigned i=0;i<3;++i)assert(!pthread_create(&producers[i],NULL,produce,(void*)(uintptr_t)i));
    uint64_t deadline=ngb_elapsed_ns()+2000000000ull;
    while(atomic_load(&completed)!=3 && ngb_elapsed_ns()<deadline)svcSleepThread(1000000);
    assert(atomic_load(&completed)==3);
    for(unsigned i=0;i<3;++i)assert(!pthread_join(producers[i],NULL));
    funlockfile(cp_file);
    combat_close();
    FILE* f=fopen(argv[1],"r");assert(f);
    unsigned rows[3]={0},lost[3]={0},flushes=0;char line[2048];
    while(fgets(line,sizeof line,f)) {
        unsigned index,n;
        if(sscanf(line,"#LOST,%u,%u",&index,&n)==2){assert(index<3);lost[index]+=n;continue;}
        if(line[0]=='F'){++flushes;continue;}
        int r=line[0]=='G'?0:line[0]=='R'?1:line[0]=='D'?2:-1;if(r<0)continue;
        uint64_t first;assert(sscanf(line+2,"%" SCNu64,&first)==1);
        assert(first==1000000u*(unsigned)r+100u*rows[r]);++rows[r];
    }
    fclose(f);
    for(unsigned i=0;i<3;++i)assert(rows[i]==512 && lost[i]==88);
    assert(flushes && !cp_file && !cp_writer_started);
    puts("PASS: blocked file writer does not block producers; ordered drain, overflow accounting and joined shutdown");
}
