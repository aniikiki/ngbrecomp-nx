/* Offline only. Child executes the *actual ARM game functions*, forked at
 * the boundary of an iteration. No elided game calls, no trace-derived
 * outputs. Child has copy-on-write guest RAM; never commit to live game.
 * Child poll callbacks are suppressed. Failures/timeouts count as misses. */
#define _GNU_SOURCE
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <signal.h>
#include <unistd.h>
#include <sys/wait.h>
#include <sys/mman.h>
enum {RAM=128u<<20,N=64,TAG=0xac000000,MAX=131072};
static struct output {unsigned n,ok,tickets,entries,func_n;unsigned funcs[2048];uint8_t regs[512];struct item{unsigned at;uint8_t value;} write[MAX];} *result;
extern unsigned dep_task;unsigned trial_variant=1,actor_fork_child;
extern uint64_t ngb_guest_polls;extern unsigned fork_regs(void*,uint64_t*);
static uint8_t *base,*seen;static unsigned written[MAX],num,prior[2][N],frame,active,stage,id,scope,initial_sp;
static uint64_t p0,e0;static pid_t child;
static unsigned funcseen[4096];
void actor_fork_entry(unsigned pc){
 if(!actor_fork_child)return;
 unsigned i=(pc*2654435761u)>>20;
 for(unsigned k=0;k<4096;k++,i=(i+1)&4095){
  if(funcseen[i]==pc)return;
  if(!funcseen[i]){funcseen[i]=pc;if(result->func_n==2048)_exit(95);result->funcs[result->func_n++]=pc;return;}
 }_exit(96);
}
void dep_bind(void*p){base=p;if(!seen){seen=calloc(RAM,1);
 result=mmap(0,sizeof(*result),PROT_READ|PROT_WRITE,MAP_SHARED|MAP_ANONYMOUS,-1,0);
 if(!seen||result==MAP_FAILED)abort();}}
void dep_key(unsigned k){active=(k>>24)==(TAG>>24);if(active){stage=k>>8&1;id=k&63;}}
void actor_begin(unsigned ph,unsigned obj,unsigned sp){
 if(!frame)return;unsigned s=ph-1,i=(obj-0x4b4e50)/0x2800;if(active||i>=N||obj!=0x4b4e50+i*0x2800)abort();
 prior[s][i]=dep_task;dep_task=TAG|(s<<8)|i;dep_key(dep_task);
 if(s && (frame==1802||frame==1808)){
  if(scope)abort();scope=1;initial_sp=sp;num=0;result->ok=0;result->func_n=0;
  uint8_t regs[512];fork_regs(regs,&e0);p0=ngb_guest_polls;
  child=fork();if(child<0)abort();
  if(!child){actor_fork_child=1;alarm(2);}
 }
}
void actor_end(void){
 if(!active)return;
 if(stage && scope){
  uint8_t regs[512];uint64_t entries;unsigned nr=fork_regs(regs,&entries);
  if(actor_fork_child){result->n=num;result->tickets=ngb_guest_polls-p0;result->entries=entries-e0;memcpy(result->regs,regs,nr);
   for(unsigned j=0;j<num;j++){unsigned at=written[j];result->write[j]=(struct item){at,base[at]};}
   result->ok=1;_exit(0);}
  int status;if(waitpid(child,&status,0)!=child)abort();
  unsigned missing=0,diff=0,nonstack=0,extra=0,gpr=0;
  if(WIFEXITED(status)&&!WEXITSTATUS(status)&&result->ok){
   for(unsigned j=0;j<result->n;j++){
    unsigned at=result->write[j].at;
    if(!seen[at])missing++;else seen[at]=2;
    if(base[at]!=result->write[j].value){diff++;nonstack+=!(at>=initial_sp-16384 && at<initial_sp+4);}
   }
   for(unsigned j=0;j<num;j++)extra+=seen[written[j]]==1;
   for(unsigned j=0;j<nr;j++)gpr+=regs[j]!=result->regs[j];
  }
  fprintf(stderr,"[NATIVE_ACTOR] frame=%u actor=%u exit=%d completed=%u writes=%u child_writes=%u diff=%u nonstack=%u missing=%u extra=%u regs=%u tickets=%llu:%u entries=%llu:%u\n",
   frame,id,status,result->ok,num,result->ok?result->n:0,diff,nonstack,missing,extra,gpr,(unsigned long long)(ngb_guest_polls-p0),result->tickets,(unsigned long long)(entries-e0),result->entries);
  if(result->ok){fprintf(stderr,"[ACTOR_CODE] %u %u",frame,id);for(unsigned j=0;j<result->func_n;j++)fprintf(stderr," %08x",result->funcs[j]);fputc('\n',stderr);}
  for(unsigned j=0;j<num;j++)seen[written[j]]=0;scope=0;
 }
 dep_task=prior[stage][id];dep_key(dep_task);
}
void dep_flip(unsigned f,unsigned k){
 if(actor_fork_child)_exit(91);
 if(active&&scope)abort();frame=f>=1801&&f<=1812?f:0;dep_key(k);
}
static inline void observe(void*ptr,unsigned n,int wr,uintptr_t pc){
 (void)pc;if(!wr||!scope||!active||!stage)return;uintptr_t a=(uintptr_t)ptr-(uintptr_t)base;if(!n||n>RAM||a>RAM-n)return;
 for(unsigned j=0;j<n;j++){unsigned off=a+j;if(!seen[off]){if(num==MAX){if(actor_fork_child)_exit(92);abort();}seen[off]=1;written[num++]=off;}}
}
#include "tsan-hooks.inc"
