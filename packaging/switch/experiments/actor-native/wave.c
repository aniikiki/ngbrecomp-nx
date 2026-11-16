/* Diagnostic only: release two worker threads after actor zero, before the
   original game starts its next actor. Never publish a worker write. */
#include <pthread.h>
#include <time.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
enum{RAM=128u<<20,TAG=0xac000000,N=64,MAX=131072};
extern unsigned dep_task,fork_regs(void*,uint64_t*);
extern uint16_t ngb_fast_page_bytes[];extern uint64_t ngb_guest_polls;
extern unsigned ngb_actor_sparse(void*,uint8_t*,const uint16_t*,uint64_t*,uint64_t*,uint16_t*,uint8_t*,uint16_t*,unsigned*,uint8_t*);
unsigned trial_variant=1,actor_fork_child;
static uint8_t *base,*initial,*seen;static uint16_t *pages;static unsigned prior[2][N],num,written[MAX],phase,id,on,frame,sp,count,limit,waves,active,join_at;
static union regs{uint8_t bytes[512];uint32_t r[128];} seed,entry;
struct job{union regs regs;uint16_t *index,*touched;uint8_t *slots,*foot;unsigned used,err,id;uint64_t polls,entries;};
static unsigned planned[32768],np;
static struct job jobs[32];static pthread_t threads[2];static _Atomic unsigned next,ready[32];
static _Thread_local struct job*current;
static unsigned word(unsigned a){unsigned v,pg=(a&0x7fffffffu)>>12;if(pg>=32768||(a&4095)>4092 || pages[a>>12]<(a&4095)+4){current->err=~0u;return 0;}current->foot[pg]=1;memcpy(&v,initial+(a&0x7fffffff),4);return v;}
static void calc(unsigned i){
 struct job*j=jobs+i;struct job*prev=NULL;
 if(i>=6){while(!atomic_load_explicit(&ready[i-1],memory_order_acquire)){}prev=jobs+i-1;}
 unsigned obj=0x4b4e50+0x2800*j->id;memcpy(&j->regs,prev?&prev->regs:&seed,sizeof seed);current=j;j->err=0;uint32_t*r=j->regs.r;
 r[3]=entry.r[3];r[4]=entry.r[4]-i;r[6]=obj;r[0]=word(obj+0x26d8);r[1]=0;
 if(r[0]){r[2]=word(r[0]+24);r[0]=word(r[0]+r[2]);if(r[0]){r[1]=word(r[0]+4);if(r[1]){r[1]=word(r[0]+r[1]);if(r[1])r[1]+=r[0];}}}
 for(unsigned k=0;k<j->used;k++)j->index[j->touched[k]]=0;
 /* Each job needs its own low actor-id byte in an otherwise shared stack page.
    Seed slot zero, and preserve it through worker initialization. */
 unsigned pg=sp>>12;unsigned prevslot=prev?prev->index[pg]:0;memcpy(j->slots,prevslot?prev->slots+4096*(prevslot-1):initial+pg*4096,4096);j->slots[sp%4096+20]=j->id;
 j->index[pg]=1;j->touched[0]=pg;j->used=1;j->polls=0;j->entries=0;
 if(!j->err&&(!prev||!prev->err))j->err=ngb_actor_sparse(&j->regs,initial,pages,&j->polls,&j->entries,j->index,j->slots,j->touched,&j->used,j->foot);
 else j->err=~0u;
 atomic_store_explicit(&ready[i],1,memory_order_release);
 }
static void *worker(void*ignored){unsigned i;while((i=atomic_fetch_add(&next,1))<limit)calc(i);return NULL;}
/* Measure the same ten calculations, including inter-job dependency forwarding.
   The longer dependency chain has one owner; no spinning on another core. */
static pthread_barrier_t start_bar,done_bar;
static _Atomic unsigned stop_worker;
static void *bench_thread(void*ignored){
 for(;;){pthread_barrier_wait(&start_bar);if(stop_worker)return NULL;
  for(unsigned i=5;i<count;i++)calc(i);
  pthread_barrier_wait(&done_bar);}
}
static uint64_t nsec(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return (uint64_t)t.tv_sec*1000000000+t.tv_nsec;}
static void bench(void){
 pthread_t thread;pthread_barrier_init(&start_bar,NULL,2);pthread_barrier_init(&done_bar,NULL,2);stop_worker=0;
 if(pthread_create(&thread,NULL,bench_thread,NULL))abort();
 for(unsigned r=0;r<36;r++){uint64_t ns[2];
  for(unsigned j=0;j<2;j++){unsigned parallel=((r+1)/2%2)^j;uint64_t t=nsec();
   for(unsigned it=0;it<8;it++){for(unsigned k=1;k<count;k++)ready[k]=0;
    if(parallel)pthread_barrier_wait(&start_bar);
    for(unsigned k=1;k<(parallel?5:count);k++)calc(k);
    if(parallel)pthread_barrier_wait(&done_bar);
   }ns[parallel]=nsec()-t;}
  if(r>=4)fprintf(stderr,"[WAVE_BENCH] wave=%u serial8=%llu parallel8=%llu\n",waves,(unsigned long long)ns[0],(unsigned long long)ns[1]);
 }
 stop_worker=1;pthread_barrier_wait(&start_bar);pthread_join(thread,NULL);pthread_barrier_destroy(&start_bar);pthread_barrier_destroy(&done_bar);
}
void dep_bind(void*p){base=p;if(!seen){initial=malloc(RAM);seen=calloc(RAM,1);pages=calloc(1,2u<<20);if(!initial||!seen||!pages)abort();
 for(unsigned i=0;i<32;i++){struct job*j=jobs+i;j->foot=calloc(32768,1);j->slots=malloc(512*4096);j->index=calloc(32768,2);j->touched=malloc(1024);if(!j->foot||!j->slots||!j->index||!j->touched)abort();}}}
void dep_key(unsigned k){active=(k>>24)==(TAG>>24);if(active){phase=k>>8&1;id=k&63;}}
void actor_begin(unsigned ph,unsigned obj,unsigned s){if(!frame)return;unsigned i=(obj-0x4b4e50)/0x2800;if(i>=64||active)abort();
 prior[ph-1][i]=dep_task;dep_task=TAG|((ph-1)<<8)|i;dep_key(dep_task);
 if(phase&&i==0&&frame>=1802&&waves<6){uint64_t dummy;fork_regs(entry.bytes,&dummy);count=entry.r[4];if(count<2||count>32||(s&4095)>4060)abort();sp=s&0x7fffffff;on=1;waves++;}
}
void actor_end(void){if(!active)return;
 if(phase&&on){
  uint64_t dummy;union regs regs;unsigned nr=fork_regs(regs.bytes,&dummy);
  if(id==0){seed=regs;
   if(waves==1){memcpy(initial,base,RAM);memcpy(pages,ngb_fast_page_bytes,2u<<20);}
   else{
    if(waves==2)memset(pages,0,2u<<20);
    for(unsigned k=0;k<np;k++){unsigned pg=planned[k];memcpy(initial+pg*4096,base+pg*4096,4096);
     pages[pg]=ngb_fast_page_bytes[pg];pages[pg+0x80000]=ngb_fast_page_bytes[pg+0x80000];}
   }
   for(unsigned i=1;i<count;i++)jobs[i].id=initial[sp+24+i];
   limit=count;join_at=1;for(unsigned i=0;i<count;i++)ready[i]=0;next=1;for(unsigned i=0;i<2;i++)if(pthread_create(threads+i,NULL,worker,NULL))abort();
  }else{unsigned pos=1;while(pos<count&&jobs[pos].id!=id)pos++;if(pos==count)abort();
   /* Join before first comparison only; all jobs used actor zero's snapshot. */
   if(pos==join_at)for(unsigned i=0;i<2;i++)pthread_join(threads[i],NULL);
   struct job*j=jobs+pos;unsigned diff=0,rd=0,extra=0,ns=0;
   for(unsigned k=0;k<num;k++){unsigned a=written[k],slot=j->index[a>>12];unsigned v=slot?j->slots[(slot-1)*4096+(a&4095)]:initial[a];if(v!=base[a]){diff++;ns+=a<sp-16384||a>=sp+4;}}
   for(unsigned k=0;k<j->used;k++){unsigned pg=j->touched[k];uint8_t*q=j->slots+4096*k;for(unsigned off=0;off<4096;off++){unsigned a=pg*4096+off;unsigned inherited=pos>=6 &&pg==(sp>>12);unsigned parentSlot=inherited?jobs[pos-1].index[pg]:0;unsigned before=parentSlot?jobs[pos-1].slots[4096*(parentSlot-1)+off]:initial[a];if(a!=sp+20&&!seen[a]&&q[off]!=before)extra++;}}
   for(unsigned k=0;k<nr;k++)rd+=regs.bytes[k]!=j->regs.bytes[k];
   fprintf(stderr,"[WAVE] wave=%u pos=%u actor=%u error=%x writes=%u diff=%u nonstack=%u extra=%u regs=%u\n",waves,pos,id,j->err,num,diff,ns,extra,rd);
   if(pos+1==count){on=0;if(waves==5 && getenv("NGB_WAVE_BENCH"))bench();
    if(waves==1){for(unsigned pg=0;pg<32768;pg++){unsigned hit=pg==sp/4096;for(unsigned k=1;k<count;k++)hit|=jobs[k].foot[pg];if(hit)planned[np++]=pg;}fprintf(stderr,"[WORLD_SNAPSHOT] wave=%u snapshot_pages=%u bytes=%u\n",waves,np,np*4096);}
   }

  }
  for(unsigned k=0;k<num;k++)seen[written[k]]=0;num=0;
 }
 dep_task=prior[phase][id];dep_key(dep_task);}
void dep_flip(unsigned f,unsigned k){frame=f>=1801&&f<=1820?f:0;dep_key(k);}
static inline void observe(void*ptr,unsigned n,int wr,uintptr_t pc){(void)pc;if(!wr||!on||!active||!phase)return;uintptr_t a=(uintptr_t)ptr-(uintptr_t)base;if(!n||n>RAM||a>RAM-n)return;
 for(unsigned i=0;i<n;i++)if(!seen[a+i]){if(num>=MAX)abort();seen[a+i]=1;written[num++]=a+i;}}
#include "tsan-hooks.inc"
