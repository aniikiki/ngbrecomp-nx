/* Compare policies on literally the same recorded execution. The oracle may
 * reuse any earlier producer of the observed byte value, including the frame-
 * initial byte. This is an offline upper bound for value forwarding schemes,
 * never a rule for returning arbitrary historical values to the real game. */
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
enum {RAM=128u<<20, R=6, P=4};
struct value {uint32_t head,last[P];uint16_t initial;};
struct version {uint32_t next,earliest[P];uint8_t val;};
static struct value *page[RAM/4096];
static struct version *hist;static unsigned maxhist,used,frame,role=5,work[R],tick[R][P];
static unsigned accepted[P],joins[P];static uint8_t *base,*old;static size_t cap;
static struct {unsigned n,at,done[P];uint8_t small[16];} pending;
unsigned trial_variant;
static struct value *cell(unsigned at){
 unsigned p=at>>12;if(!page[p]){page[p]=calloc(4096,sizeof(**page));if(!page[p])abort();}
 return &page[p][at&4095];
}
static inline int matrices(unsigned at){return at-0x950180u<64||at-0xd52688u<4;}
static void finish(void){
 if(!pending.n)return;unsigned n=pending.n;pending.n=0;const uint8_t* prev=n>16?old:pending.small;
 for(unsigned j=0;j<n;j++){
  unsigned at=pending.at+j;struct value *c=cell(at);
  if(!c->initial)c->initial=1u+prev[j];unsigned val=base[at];
  if(val!=prev[j])memcpy(c->last,pending.done,sizeof c->last);
  if(val+1u==c->initial)continue;
  unsigned idx=c->head;while(idx && hist[idx].val!=val)idx=hist[idx].next;
  if(!idx){
   if(used+1>=maxhist){maxhist=maxhist?maxhist*2:65536;hist=realloc(hist,maxhist*sizeof(*hist));if(!hist)abort();}
   idx=++used;hist[idx].val=val;hist[idx].next=c->head;c->head=idx;
   memcpy(hist[idx].earliest,pending.done,sizeof c->last);
  }else for(unsigned i=1;i<P;i++)if(pending.done[i]<hist[idx].earliest[i])hist[idx].earliest[i]=pending.done[i];
 }
}
void dep_bind(void*p){base=p;}
void dep_key(unsigned k){finish();role=k==0x1ca790?1:k==0x1cb9a0?2:k==0x151150?3:k==0x320e0?4:5;}
void dep_flip(unsigned f,unsigned k){
 finish();if(frame){
  unsigned tot=0;for(unsigned r=1;r<R;r++)tot+=work[r];
  fprintf(stderr,"[VERSIONS] %u total %u",frame,tot);
  for(unsigned i=0;i<P;i++){unsigned m=0;for(unsigned r=1;r<R;r++)if(tick[r][i]>m)m=tick[r][i];fprintf(stderr," %u:%u:%u",m,accepted[i],joins[i]);}fputc('\n',stderr);
  for(unsigned p=0;p<RAM/4096;p++)if(page[p])memset(page[p],0,4096*sizeof(**page));
 }
 used=0;memset(work,0,sizeof work);memset(tick,0,sizeof tick);memset(joins,0,sizeof joins);memset(accepted,0,sizeof accepted);
 frame=f>=1801 && f<=1812?f:0;trial_variant=!!frame;dep_key(k);
}
static inline void observe(void*addr,unsigned n,int wr,uintptr_t pc){
 (void)pc;if(!frame)return;finish();
 uintptr_t at=(uintptr_t)addr-(uintptr_t)base;if(!n||n>RAM||at>RAM-n)return;
 unsigned *t=tick[role],next[P];memcpy(next,t,sizeof next);
 if(!wr)for(unsigned j=0;j<n;j++){
   struct value *c=cell(at+j);unsigned val=base[at+j],early[P];
   if(!c->initial)c->initial=val+1;
   memcpy(early,c->last,sizeof early);
   if(c->initial==val+1u)memset(early,0,sizeof early);
   else{
    unsigned idx=c->head;while(idx && hist[idx].val!=val)idx=hist[idx].next;
    if(idx)memcpy(early,hist[idx].earliest,sizeof early);
    /* A native/unsampled write can be observed only here; do not invent an origin. */
   }
   for(unsigned i=0;i<P;i++){
    unsigned dep=c->last[i];
    if(i==3 || (i==1 && matrices(at+j)) || (i==2 && c->initial==val+1u)){
      if(early[i]<dep)accepted[i]++;dep=early[i];}
    if(dep>next[i])next[i]=dep;
   }
 }
 ++work[role];for(unsigned i=0;i<P;i++){joins[i]+=next[i]>t[i];t[i]=next[i]+1;}
 if(wr){
  pending.n=n;pending.at=at;memcpy(pending.done,t,sizeof next);
  if(n>16 && n>cap){old=realloc(old,n);if(!old)abort();cap=n;}
  memcpy(n>16?old:pending.small,addr,n);
 }
}
#include "tsan-hooks.inc"
