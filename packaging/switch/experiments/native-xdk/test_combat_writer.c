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
#include "diagnostics_flag.h"
#include "combat_perf.inc"

static atomic_uint completed;
static void test_story_charge(void) {
    uint8_t *ram=calloc(1,0xdc0000);assert(ram);
    ngb_combat_guest(97,255,0,0,0,0,0,0,0,0,ram);
    assert(!ngb_combat_active());
    ngb_combat_new_game_press();
    ngb_combat_guest(98,255,0,0,0,0,0,0,0,0,ram);
    assert(ngb_combat_active());
    cp_menu_until=1;
    ngb_combat_guest(99,255,0,0,0,0,0,0,0,0,ram);
    assert(!ngb_combat_active());
    unsigned start=atomic_load(&cp_ring[0].head);
    ram[0x4968b4]=0xb9;
    ram[0x58a570]=0x83;ram[0x58a571]=1; /* Kitetsu */
    ram[0x5895e2]=2;ram[0x5895e4]=221;ram[0x5895e8]=220;
    uint32_t ryu=0x4b4e50, position=0xbf800000u;
    memcpy(ram+0x4b5710,&position,4);
    for(unsigned i=0;i<4;i++){
        uint8_t *fx=ram+0x5b6930+i*0x180u;
        const unsigned types[]={0xb0,0xe2,1,0x3f};
        fx[0x178]=i!=2;fx[0x17a]=types[i];
        if(i!=3)memcpy(fx+0xf8,&ryu,4);
    }
    ngb_combat_guest(101,255,1,0,1000,1000,0,0,0,0,ram);
    assert(ngb_combat_active() && atomic_load(&cp_ring[0].head)==start+2);
    CombatRow *g=&cp_ring[0].rows[start%CP_CAP],*u=&cp_ring[0].rows[(start+1)%CP_CAP];
    assert(g->kind=='G' && g->v[0]==101 && u->kind=='U' && u->n==21 && u->v[0]==g->v[0]);
    assert(u->v[2]==0xb9 && u->v[3]==0x183 && u->v[6]==2 && u->v[7]==221 && u->v[9]==220);
    assert(u->v[12]==position && u->v[15]==1 && u->v[16]==1);
    assert(u->v[17]==(UINT64_C(1)<<63) && !u->v[18]);
    assert(u->v[19]==(UINT64_C(1)<<48) && u->v[20]==(UINT64_C(1)<<34));
    unsigned render_head=atomic_load(&cp_ring[1].head);
    uint64_t phase[31]={101, [30]=12345},material[14]={101};
    ngb_combat_row('A',phase,31);
    ngb_combat_row('L',material,14);
    assert(atomic_load(&cp_ring[1].head)==render_head+2);
    CombatRow *a=&cp_ring[1].rows[render_head%CP_CAP];
    assert(a->n==31 && a->v[30]==12345);
    ngb_combat_file(0,0,1024,1500);
    ngb_combat_file(1,0,100,2000);
    ngb_combat_file(1,1,4096,3600);
    ngb_combat_guest(102,255,1,0,0,0,0,0,0,0,ram);
    assert(ngb_combat_active() && atomic_load(&cp_ring[0].head)==start+3);
    g=&cp_ring[0].rows[(start+2)%CP_CAP];
    assert(g->n==23 && g->v[13]==1 && g->v[14]==1024 && g->v[15]==1);
    assert(g->v[16]==2 && g->v[17]==4196 && g->v[18]==5);
    assert(g->v[19]==1 && g->v[20]==4096 && g->v[21]==3);
    // A fresh boot entering Phase 5 must arm the recorder on its own. The
    // following transition has no live player; only a guest-frame row survives.
    cp_entered_game=0;
    ngb_combat_guest(104,33,3,0,1000,1000,0,0,0,0,ram);
    assert(ngb_combat_active() && atomic_load(&cp_ring[0].head)==start+5);
    ram[0xdb9c6e]=77;
    ngb_combat_guest(105,255,0,0,0,0,0,0,0,0,ram);
    g=&cp_ring[0].rows[(start+5)%CP_CAP];
    assert(ngb_combat_active() && atomic_load(&cp_ring[0].head)==start+6);
    assert(g->kind=='G' && g->v[0]==105 && g->v[22]==77);
    uint64_t native[37] = {[0]=105, [36]=2};
    unsigned head=atomic_load(&cp_ring[0].head);
    ngb_combat_row('N',native,37);
    CombatRow *n=&cp_ring[0].rows[head%CP_CAP];
    assert(atomic_load(&cp_ring[0].head)==head+1 && n->kind=='N' && n->n==37 && n->v[36]==2);
    free(ram);
}
static void* produce(void* argument) {
    unsigned ring=(unsigned)(uintptr_t)argument;
    const unsigned kinds[]={'G','R','D'},columns[]={23,31,5};
    for(unsigned i=0;i<600;++i) {
        uint64_t values[32];for(unsigned j=0;j<32;++j)values[j]=1000000*ring+100*i+j;
        if (ring==1 && (i&1)) ngb_combat_row('E',values,17);
        else ngb_combat_row(kinds[ring],values,columns[ring]);
    }
    atomic_fetch_add(&completed,1);return NULL;
}
int main(int argc,char** argv) {
    assert(argc==2 && !ngb_diagnostics_requested(".") && !ngb_diagnostics_requested("no-such-file/" NGB_DIAGNOSTICS_FLAG));
    assert(combat_open(argv[1]) && ngb_diagnostics_requested(argv[1]));
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
        int r=line[0]=='G'?0:(line[0]=='R'||line[0]=='E')?1:line[0]=='D'?2:-1;if(r<0)continue;
        uint64_t first;assert(sscanf(line+2,"%" SCNu64,&first)==1);
        assert(first==1000000u*(unsigned)r+100u*rows[r]);++rows[r];
    }
    fclose(f);
    for(unsigned i=0;i<3;++i)assert(rows[i]==512 && lost[i]==88);
    assert(flushes && !cp_file && !cp_writer_started);
    test_story_charge();
    puts("PASS: blocked file writer does not block producers; ordered drain, overflow accounting and joined shutdown");
}
