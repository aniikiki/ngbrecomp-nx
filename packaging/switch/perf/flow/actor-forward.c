/* For loop 147ECD: allow per-actor private stack/matrix state, and compare
 * a true producer with immutable loop-entry values and last writer. Includes
 * fully serialized outside edges only as unpriced gaps. No game reordering. */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
enum {RAM=128u<<20,N=64,P=5,TAG=0xac000000};
struct byte {uint32_t time[P];unsigned char first,init;};
static struct byte *pages[RAM/4096];static unsigned tick[N][P],work[N],frame,active,id,prior[2][N],stack[2][N],stage;
static unsigned at_,n_,t_[P],owner;static uint8_t *base,*old,small[16];static size_t cap;
extern unsigned dep_task;unsigned trial_variant=1;
static struct byte *cell(unsigned a){struct byte **p=&pages[a>>12];if(!*p && !(*p=calloc(4096,sizeof **p)))abort();return *p+(a&4095);}
static void finish(void){
 if(!n_)return;unsigned len=n_;n_=0;const uint8_t *before=len>16?old:small;
 for(unsigned j=0;j<len;j++){struct byte*b=cell(at_+j);if(!b->init){b->init=1;b->first=before[j];}
  if(before[j]!=base[at_+j])memcpy(b->time,t_,sizeof t_);
  else for(unsigned v=2;v<=3;v++)if(t_[v]<b->time[v])b->time[v]=t_[v];
 }
}
void dep_bind(void*p){base=p;}
void dep_key(unsigned k){finish();active=(k>>24)==(TAG>>24);if(active){stage=(k>>8)&1;id=k&63;}}
void actor_begin(unsigned ph,unsigned obj,unsigned sp){
 if(!frame)return;unsigned s=ph-1,i=(obj-0x4b4e50)/0x2800;if(obj<0x4b4e50||(obj-0x4b4e50)%0x2800||i>=N||active)abort();
 prior[s][i]=dep_task;stack[s][i]=sp;dep_task=TAG|(s<<8)|i;dep_key(dep_task);
}
void actor_end(void){if(active){dep_task=prior[stage][id];dep_key(dep_task);}}
void dep_flip(unsigned f,unsigned k){
 finish();if(frame){unsigned total=0,m[P]={0};for(unsigned i=0;i<N;i++){total+=work[i];for(unsigned j=0;j<P;j++)if(tick[i][j]>m[j])m[j]=tick[i][j];}
  fprintf(stderr,"[ACTOR_FORWARD] %u %u %u %u %u %u %u\n",frame,total,m[0],m[1],m[2],m[3],m[4]);
  for(unsigned i=0;i<RAM/4096;i++)if(pages[i])memset(pages[i],0,4096*sizeof(struct byte));}
 memset(tick,0,sizeof tick);memset(work,0,sizeof work);frame=f>=1801&&f<=1812?f:0;dep_key(k);
}
static inline void observe(void*ptr,unsigned n,int wr,uintptr_t pc){
 (void)pc;if(!frame||!active||!stage)return;finish();uintptr_t a=(uintptr_t)ptr-(uintptr_t)base;if(!n||n>RAM||a>RAM-n)return;
 unsigned sp=stack[stage][id],*t=tick[id];
 if(!wr)for(unsigned j=0;j<n;j++){unsigned off=a+j;struct byte*b=cell(off);
   int scratch=(off>=sp-16384 && off<sp+4)||(off-0x950180u<64)||(off-0xd52688u<4);
   for(unsigned v=0;v<P;v++){
    if(v>=1&&scratch)continue;
    
    // Only two candidate collision accumulators are additionally private.
    if(v==3 && ((off-0x7a6870u<4)||(off-0xdb67c0u<4)))continue;
    if(v==4)continue;
    if(b->time[v]>t[v])t[v]=b->time[v];}
 }
 for(unsigned v=0;v<P;v++)t[v]++;++work[id];
 if(wr){at_=a;n_=n;memcpy(t_,t,sizeof t_);if(n>16&&n>cap){old=realloc(old,n);if(!old)abort();cap=n;}memcpy(n>16?old:small,ptr,n);}
}
#include "tsan-hooks.inc"
