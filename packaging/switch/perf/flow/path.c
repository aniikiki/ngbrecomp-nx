/* Offline dataflow model: count one unit per instrumented guest RAM access.
 * Five serial role streams; the maximum chain includes read-after-write,
 * write-after-read and write-after-write across all addressed bytes. This
 * predicts neither CPU cycles nor whether it is safe to run tasks in parallel. */
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
enum { RAM=128u<<20, ROLES=6 };
struct byte_times { uint32_t write,read; };
static struct byte_times *page[RAM/4096];
static unsigned key,frame,role=5,work[ROLES],end[ROLES],transitions;
static uint8_t *base;
unsigned trial_variant;
static inline unsigned maximum(unsigned a,unsigned b){return a>b?a:b;}
void dep_bind(void *p){base=p;}
void dep_key(unsigned k){
    unsigned r=k==0x1ca790?1:k==0x1cb9a0?2:k==0x151150?3:k==0x320e0?4:5;
    if(r!=role && frame)transitions++;
    key=k;role=r;
}
void dep_flip(unsigned f,unsigned k){
    if(frame){
        fprintf(stderr,"[FLOW_PATH] %u switches=%u",frame,transitions);
        for(unsigned i=1;i<ROLES;i++)fprintf(stderr," %u:%u:%u",i,work[i],end[i]);
        fputc('\n',stderr);
        for(unsigned p=0;p<RAM/4096;p++)if(page[p])memset(page[p],0,4096*sizeof(*page[p]));
    }
    memset(work,0,sizeof work);memset(end,0,sizeof end);transitions=0;
    frame=f>=1801 && f<=1812?f:0;trial_variant=!!frame;dep_key(k);
}
static inline void observe(void *addr,unsigned n,int wr,uintptr_t pc){
    (void)pc;uintptr_t at=(uintptr_t)addr-(uintptr_t)base;
    if(!frame||!n||n>RAM||at>RAM-n)return;
    unsigned after=end[role];
    for(unsigned j=0;j<n;j++){
        unsigned i=(at+j)>>12;
        if(!page[i]){page[i]=calloc(4096,sizeof(*page[i]));if(!page[i])abort();}
        struct byte_times x=page[i][(at+j)&4095];
        after=maximum(after,x.write);
        if(wr)after=maximum(after,x.read);
    }
    if(++after==0)abort();
    end[role]=after;++work[role];
    for(unsigned j=0;j<n;j++){
        struct byte_times *x=&page[(at+j)>>12][(at+j)&4095];
        if(wr){x->write=after;x->read=0;}else x->read=maximum(x->read,after);
    }
}
#include "tsan-hooks.inc"
