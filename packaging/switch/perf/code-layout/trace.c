/* Offline only. Follow the game thread, including calls into the native host.
   No code, game memory, or screenshots are included in the trace, only PCs. */
#include "frida-gum.h"
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <signal.h>
#include <execinfo.h>
#include <unistd.h>
extern char __executable_start,etext;
struct block {uint64_t pc;uint32_t bytes,frame;};
static struct block *trace;
static unsigned used,frame,lost,empty,bad;
static GumStalker *stalker;
static GumEventSink *sink;
enum { CAP=1u<<26 };
static void record(const GumEvent *ev,GumCpuContext *context,gpointer data){
    (void)context;(void)data;
    if(ev->type!=GUM_BLOCK || !frame)return;
    uintptr_t pc=(uintptr_t)ev->block.start,end=(uintptr_t)ev->block.end;
    if(end==pc){++empty;return;}
    if(end<pc || ((end-pc)&3) || end-pc>UINT32_MAX){++bad;return;}
    if(used==CAP){++lost;return;}
    trace[used++]=(struct block){pc,(uint32_t)(end-pc),frame};
}
static void crash(int sig){void *p[32];int n=backtrace(p,32);backtrace_symbols_fd(p,n,2);_exit(128+sig);}
void layout_frame(unsigned next){
    if(next==1800){
        trace=mmap(NULL,sizeof(*trace)*CAP,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
        if(trace==MAP_FAILED)abort();
        gum_init_embedded();if(!gum_stalker_is_supported())abort();
        stalker=gum_stalker_new();sink=gum_event_sink_make_from_callback(GUM_BLOCK,record,NULL,NULL);
        signal(SIGABRT,crash);fprintf(stderr,"[BLOCK_START] frame %u\n",next);
        frame=next;gum_stalker_follow_me(stalker,NULL,sink);
    }else if(next>=1801 && next<1804){frame=0;fprintf(stderr,"[BLOCK_PROGRESS] next=%u used=%u bad=%u empty=%u lost=%u\n",next,used,bad,empty,lost);frame=next;}
    else if(next==1804){
        frame=0;gum_stalker_unfollow_me(stalker);gum_stalker_flush(stalker);
        fprintf(stderr,"[BLOCK_STATS] recorded=%u overflow=%u empty=%u invalid=%u\n",used,lost,empty,bad);
        if(lost || !used || bad)abort();
        FILE *f=fopen(getenv("NGB_CODE_TRACE"),"wb");if(!f)abort();
        uint64_t h[4]={0x4e4742434f444531ull,(uintptr_t)&__executable_start,(uintptr_t)&etext,used};
        if(fwrite(h,sizeof(h),1,f)!=1 || fwrite(trace,sizeof(*trace),used,f)!=used || fclose(f))abort();
        fprintf(stderr,"[BLOCK_TRACE] records=%u frames=1800..1803\n",used);
    }
}
