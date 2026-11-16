/* Can later actors take external inputs from one initial snapshot?
 * Count each byte once per actor; any own store, even unchanged, defines
 * that byte locally. Do not confuse recurring clears with true RAW edges.
 * Native noninstrumented writers and live callbacks remain limitations. */
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
enum {RAM=128u<<20,N=64,TAG=0xac000000,K=6};
struct row {unsigned id,at,n,read[K],diff[K];};
static struct row rows[128];static unsigned used,which[2][N],prior[2][N],frame,stage,id,active;
static uint8_t *base,*snap,*seen;static unsigned nonmatch[RAM/4096];
extern unsigned dep_task;unsigned trial_variant=1;
void dep_bind(void*p){base=p;if(!snap){snap=malloc(RAM);seen=calloc(RAM,1);if(!snap||!seen)abort();}}
void dep_key(unsigned k){active=(k>>24)==(TAG>>24);if(active){stage=(k>>8)&1;id=k&63;}}
void actor_begin(unsigned phase,unsigned obj,unsigned sp){
 if(!frame)return;unsigned s=phase-1,i=(obj-0x4b4e50)/0x2800;if(active||i>=N||obj!=0x4b4e50+0x2800*i)abort();
 if(s){if(!used)memcpy(snap,base,RAM);if(++used>=128)abort();
 rows[used]=(struct row){.id=i,.at=sp};which[s][i]=used;}
 prior[s][i]=dep_task;dep_task=TAG|(s<<8)|i;dep_key(dep_task);
}
void actor_end(void){if(active){dep_task=prior[stage][id];dep_key(dep_task);}}
void dep_flip(unsigned f,unsigned k){
 if(frame){
  for(unsigned i=1;i<=used;i++){struct row*r=&rows[i];fprintf(stderr,"[ACTOR_INPUT] %u %u",frame,r->id);
   for(unsigned c=0;c<K;c++)fprintf(stderr," %u:%u",r->diff[c],r->read[c]);fputc('\n',stderr);}
  for(unsigned n=0;n<4;n++){unsigned best=0;for(unsigned j=1;j<RAM/4096;j++)if(nonmatch[j]>nonmatch[best])best=j;
   if(nonmatch[best])fprintf(stderr,"[INPUT_PAGE] %u %08x %u\n",frame,best*4096,nonmatch[best]);nonmatch[best]=0;}
  memset(nonmatch,0,sizeof nonmatch);memset(seen,0,RAM);
 }
 used=0;frame=f>=1801&&f<=1812?f:0;dep_key(k);
}
static inline void observe(void*ptr,unsigned n,int wr,uintptr_t pc){
 (void)pc;if(!frame||!active||!stage)return;uintptr_t a=(uintptr_t)ptr-(uintptr_t)base;if(!n||n>RAM||a>RAM-n)return;
 unsigned slot=which[stage][id];struct row*r=&rows[slot];unsigned sp=r->at;
 for(unsigned j=0;j<n;j++){unsigned at=a+j;if(seen[at]==slot)continue;seen[at]=slot;if(wr)continue;
 unsigned c=at>=sp-16384 && at<sp+4?0:at-0x950180u<64 || at-0xd52688u<4?1:
 at-0x7a6870u<4 || at-0xdb67c0u<4?2:at-0x4b4e50u<64*0x2800u?3:at>=0x1000000?4:5;
 r->read[c]++;if(snap[at]!=base[at]){r->diff[c]++;if(c>=3)nonmatch[at>>12]++;}
 }
}
#include "tsan-hooks.inc"
