/* Exact byte-level optimistic commit check over real original game RAM events.
 * Can an actor run on the snapshot available at wave start and commit its
 * first-read / final-write set? Per-actor writes define subsequent reads,
 * even when equal. Fail closed if a given actor observes external changes
 * after its first access. Trace only; does not change the original game. */
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
enum {RAM=128u<<20,TAG=0xac000000,N=64};
extern unsigned dep_task;unsigned trial_variant=1;
static unsigned frame,active,stage,id,prior[2][N],sp0,seq;
static uint8_t *base,*snap,*local,*seen;static unsigned *touched,used,cap;
static unsigned stable,unstable,wdiff,inputs,skip,work,pending_at,pending_n;
static void flush(void){if(pending_n){memcpy(local+pending_at,base+pending_at,pending_n);pending_n=0;}}
void dep_bind(void*p){base=p;if(!snap){snap=malloc(RAM);local=malloc(RAM);seen=calloc(RAM,1);if(!snap||!local||!seen)abort();}}
void dep_key(unsigned k){flush();active=(k>>24)==(TAG>>24);if(active){stage=k>>8&1;id=k&63;}}
static int scratch(unsigned a){return (a>=sp0-16384 && a<sp0+4)||(a-0x950180u<64)||(a-0xd52688u<4);}
void actor_begin(unsigned ph,unsigned obj,unsigned sp){
 if(!frame)return;unsigned s=ph-1,i=(obj-0x4b4e50)/0x2800;if(active||i>=N||obj!=0x4b4e50+i*0x2800)abort();
 if(s){if(!seq)memcpy(snap,base,RAM);seq++;sp0=sp;used=stable=unstable=wdiff=inputs=skip=work=0;}
 prior[s][i]=dep_task;dep_task=TAG|(s<<8)|i;dep_key(dep_task);
}
void actor_end(void){
 if(!active)return;flush();
 if(stage){unsigned final=0,mismatch=0;for(unsigned i=0;i<used;i++){unsigned a=touched[i];if(seen[a]&2){++final;mismatch+=base[a]!=local[a];}seen[a]=0;}
  fprintf(stderr,"[ACTOR_TX] %u %u %u work=%u unique=%u input=%u initial_diff=%u interleave=%u writes=%u final_diff=%u scratch=%u\n",frame,seq,id,work,used,inputs,stable,unstable,final,mismatch,skip);}
 dep_task=prior[stage][id];dep_key(dep_task);
}
void dep_flip(unsigned f,unsigned k){
 flush();if(active)abort();seq=0;frame=f>=1801&&f<=1812?f:0;dep_key(k);
}
static inline void observe(void*ptr,unsigned n,int wr,uintptr_t pc){
 (void)pc;if(!frame||!active||!stage)return;flush();uintptr_t a=(uintptr_t)ptr-(uintptr_t)base;if(!n||n>RAM||a>RAM-n)return;
 ++work;for(unsigned j=0;j<n;j++){unsigned off=a+j;if(scratch(off)){++skip;continue;}
  if(!seen[off]){
   if(used==cap){cap=cap?cap*2:65536;touched=realloc(touched,cap*sizeof(*touched));if(!touched)abort();}
   touched[used++]=off;seen[off]=1;local[off]=base[off];
   if(!wr){inputs++;stable+=snap[off]!=base[off];}
  }else if(!wr && base[off]!=local[off]){unstable++;local[off]=base[off];}
  if(wr)seen[off]|=2;
 }
 if(wr){pending_at=a;pending_n=n;}
}
#include "tsan-hooks.inc"
