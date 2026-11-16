/* Offline best case for distributing iterations of two actual game loops.
 * Only original actor-body RAM operations have cost. Outside work and barriers
 * are free. Compare RAW constraints with explicit scratch privatization and
 * ideal zero communication in the same execution. No writes skipped in game. */
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
enum {RAM=128u<<20,N=64,P=3,S=2,TAG=0xac000000};
struct byte {unsigned t[2],trace,pc,who;};
static struct byte *pages[S][RAM/4096];
static struct hop {unsigned parent,at,from,into,from_id,into_id,before;} *hist;
static unsigned used,capacity,trace[S][N],wpc;extern char __executable_start;
static unsigned time_[S][N][P],total[S],enter[S][N],prior[S][N],stack[S][N],frame,active,stage,id;
static unsigned at_,n_,t_[2],ss,private_;
static uint8_t *base,*old,small[16];static unsigned cap;
extern unsigned dep_task;unsigned trial_variant=1;
static struct byte *byteat(unsigned s,unsigned a){
 struct byte **p=&pages[s][a>>12];if(!*p && !(*p=calloc(4096,sizeof **p)))abort();return *p+(a&4095);
}
static void finish(void){
 if(!n_)return;const unsigned char *before=n_>16?old:small;
 for(unsigned j=0;j<n_;j++)if(before[j]!=base[at_+j]){
  struct byte *b=byteat(ss,at_+j);b->t[0]=t_[0];b->t[1]=private_?0:t_[1];b->trace=trace[ss][id];b->pc=wpc;b->who=id;
 }n_=0;
}
void dep_bind(void *p){base=p;}
void dep_key(unsigned k){finish();active=(k>>24)==(TAG>>24);if(active){stage=(k>>8)&1;id=k&63;}}
void actor_begin(unsigned phase,unsigned obj,unsigned sp){
 if(!frame)return;
 if(obj<0x4b4e50 || (obj-0x4b4e50)%0x2800 || (obj-0x4b4e50)/0x2800>=64 || active)abort();
 unsigned s=phase-1,i=(obj-0x4b4e50)/0x2800;prior[s][i]=dep_task;stack[s][i]=sp;
 dep_task=TAG|(s<<8)|i;dep_key(dep_task);++enter[s][i];
}
void actor_end(void){if(!active)return;dep_task=prior[stage][id];dep_key(dep_task);}
void dep_flip(unsigned f,unsigned k){
 finish();if(frame)for(unsigned s=0;s<S;s++){
  unsigned max[P]={0},owners=0,calls=0;
  for(unsigned i=0;i<N;i++){owners+=!!enter[s][i];calls+=enter[s][i];for(unsigned j=0;j<P;j++)if(time_[s][i][j]>max[j])max[j]=time_[s][i][j];}
  fprintf(stderr,"[ACTOR_PATH] frame=%u loop=%u calls=%u actors=%u total=%u raw=%u private=%u independent=%u\n",frame,s+1,calls,owners,total[s],max[0],max[1],max[2]);
  unsigned best=0;for(unsigned i=1;i<N;i++)if(time_[s][i][1]>time_[s][best][1])best=i;
  for(unsigned h=trace[s][best];h;h=hist[h].parent){
   struct hop v=hist[h];fprintf(stderr,"[ACTOR_JOIN] %u %u %08x %x %x %u %u %u\n",frame,s+1,v.at,v.from,v.into,v.from_id,v.into_id,v.before);
  }
  for(unsigned i=0;i<RAM/4096;i++)if(pages[s][i])memset(pages[s][i],0,4096*sizeof(struct byte));
 }
 used=0;memset(trace,0,sizeof trace);memset(time_,0,sizeof time_);memset(total,0,sizeof total);memset(enter,0,sizeof enter);
 frame=(f>=1801&&f<=1812)?f:0;/* Keep instrumented private/local calls across fiber suspension. */dep_key(k);
}
static inline void observe(void *ptr,unsigned n,int wr,uintptr_t pc){
 (void)pc;if(!frame || !active)return;finish();uintptr_t a=(uintptr_t)ptr-(uintptr_t)base;if(!n||n>RAM||a>RAM-n)return;
 unsigned sp=stack[stage][id],*t=time_[stage][id];
 unsigned priv=(a>=sp-16384 && a+n<=sp+4)||(a>=0x950180 && a+n<=0x9501c0)||(a>=0xd52688 && a+n<=0xd5268c);
 unsigned pre=t[1],where=0,code=(unsigned)(pc-(uintptr_t)&__executable_start);
 if(!wr)for(unsigned j=0;j<n;j++){struct byte*b=byteat(stage,a+j);if(b->t[0]>t[0])t[0]=b->t[0];if(!priv && b->t[1]>t[1]){t[1]=b->t[1];where=a+j;}}
 if(t[1]>pre){struct byte*b=byteat(stage,where);
  if(used+1>=capacity){capacity=capacity?capacity*2:4096;hist=realloc(hist,capacity*sizeof(*hist));if(!hist)abort();}
  hist[++used]=(struct hop){b->trace,where,b->pc,code,b->who,id,t[1]};trace[stage][id]=used;}
 for(unsigned j=0;j<P;j++)t[j]++;++total[stage];
 if(wr){wpc=code;at_=a;n_=n;ss=stage;private_=priv;memcpy(t_,t,sizeof t_);if(n>16&&n>cap){old=realloc(old,n);if(!old)abort();cap=n;}memcpy(n>16?old:small,ptr,n);}
}
#include "tsan-hooks.inc"
