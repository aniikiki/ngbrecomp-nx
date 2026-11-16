/* Optimistic counterfactual: only a value-changing store followed by a read
 * constrains two roles. Preserve each role's program order; charge one unit
 * per observed RAM operation (even unchanged stores). Trace the last critical
 * producer of each join, not frequencies of arbitrary shared byte accesses. */
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
enum { RAM=128u<<20, ROLES=6 };
struct value {uint32_t time,chain,pc;};
struct hop {uint32_t parent,at,frompc,topc,time,worker;};
static struct hop *hops;static unsigned used,capacity;
static struct value *page[RAM/4096],last[ROLES];
static unsigned frame,role=5,work[ROLES];
static uint8_t *base,*old;static size_t cap;
static struct {unsigned n,at,owner;struct value v;uint8_t small[16];} pending;
unsigned trial_variant;extern char __executable_start;
static struct value *cell(unsigned at){
    unsigned p=at>>12;if(!page[p]){page[p]=calloc(4096,sizeof(**page));if(!page[p])abort();}
    return &page[p][at&4095];
}
static void finish(void){
    if(!pending.n)return;
    unsigned at=pending.at;const uint8_t *prior=pending.n>16?old:pending.small;
    for(unsigned j=0;j<pending.n;j++)if(prior[j]!=base[at+j])*cell(at+j)=pending.v;
    pending.n=0;
}
void dep_bind(void *p){base=p;}
void dep_key(unsigned k){
    finish();role=k==0x1ca790?1:k==0x1cb9a0?2:k==0x151150?3:k==0x320e0?4:5;
}
void dep_flip(unsigned f,unsigned k){
    finish();
    if(frame){
        unsigned best=1,total=0;
        for(unsigned i=1;i<ROLES;i++){total+=work[i];if(last[i].time>last[best].time)best=i;}
        fprintf(stderr,"[RAW_PATH] %u total=%u critical=%u end=%u joins=%u\n",frame,total,last[best].time,best,used);
        unsigned t=last[best].time,here=best;
        for(unsigned j=last[best].chain;j;j=hops[j].parent){
            struct hop h=hops[j];fprintf(stderr,"[RAW_HOP] %u role=%u length=%u at=%08x write=%x read=%x\n",frame,here,t-h.time,h.at,h.frompc,h.topc);
            t=h.time;here=h.worker;
        }
        fprintf(stderr,"[RAW_ROOT] %u role=%u length=%u\n",frame,here,t);
        for(unsigned p=0;p<RAM/4096;p++)if(page[p])memset(page[p],0,4096*sizeof(*page[p]));
    }
    used=0;memset(work,0,sizeof work);memset(last,0,sizeof last);
    frame=f>=1801 && f<=1812?f:0;trial_variant=!!frame;dep_key(k);
}
static inline void observe(void *addr,unsigned n,int wr,uintptr_t pc){
    if(!frame)return;
    finish();uintptr_t at=(uintptr_t)addr-(uintptr_t)base;
    if(!n||n>RAM||at>RAM-n)return;
    unsigned code=(unsigned)(pc-(uintptr_t)&__executable_start);
    struct value *v=&last[role];
    if(!wr){
        unsigned limit=v->time,where=0;struct value src={0};
        for(unsigned j=0;j<n;j++){
            struct value s=*cell(at+j);
            if(s.time>limit){limit=s.time;where=at+j;src=s;}
        }
        if(limit>v->time){
            if(used+1>=capacity){capacity=capacity?capacity*2:4096;hops=realloc(hops,capacity*sizeof(*hops));if(!hops)abort();}
            unsigned owner=src.chain>>29,idx=src.chain&0x1fffffffu;
            hops[++used]=(struct hop){idx,where,src.pc,code,limit,owner};
            v->chain=used;v->time=limit;
        }
    }
    ++v->time;++work[role];
    if(wr){
        pending.n=n;pending.at=at;pending.v=(struct value){v->time,(role<<29)|v->chain,code};
        if(n>16 && n>cap){old=realloc(old,n);if(!old)abort();cap=n;}
        memcpy(n>16?old:pending.small,addr,n);
    }
}
#include "tsan-hooks.inc"
