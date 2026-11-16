"""Run the actual devkitA64 worker object on a separate pthread. Its only
game input is an immutable RAM snapshot plus register arguments. Check its
entire 128 MiB output delta, every observed original write and the final
architectural register file. Never publish speculative output."""
from pathlib import Path
s=(Path(__file__).resolve().parents[2]/'perf/flow/actor-fork.c').read_text()
s='#include <pthread.h>\n'+s
i=s.index('static struct output');j=s.index('extern unsigned dep_task;',i)
s=s[:i]+'''extern unsigned ngb_actor_native(void*,unsigned char*,const uint16_t*,uint64_t*,uint64_t*);
extern uint16_t ngb_fast_page_bytes[];
static uint8_t *copy_,*initial;static uint16_t *pages;static uint8_t outregs[512];static unsigned nr,err;
static uint64_t ticks,ent;static pthread_t worker;
static void *run_actor(void*unused){(void)unused;err=ngb_actor_native(outregs,copy_,pages,&ticks,&ent);return NULL;}
'''+s[j:]
a=s.index('static unsigned funcseen');b=s.index('void dep_key',a)
s=s[:a]+'''void dep_bind(void*p){base=p;if(!seen){seen=calloc(RAM,1);copy_=malloc(RAM);initial=malloc(RAM);pages=malloc(2u<<20);if(!seen||!copy_||!initial||!pages)abort();}}
'''+s[b:]
a=s.index('  if(scope)abort();scope=1;');b=s.index('\n }',a)
s=s[:a]+'''  if(scope)abort();scope=1;initial_sp=sp;num=0;
  nr=fork_regs(outregs,&e0);ticks=p0=ngb_guest_polls;ent=0;
  memcpy(initial,base,RAM);memcpy(copy_,initial,RAM);memcpy(pages,ngb_fast_page_bytes,2u<<20);
  if(pthread_create(&worker,NULL,run_actor,NULL))abort();
'''+s[b:]
a=s.index('  uint8_t regs[512];uint64_t entries;');b=s.index('  for(unsigned j=0;j<num;j++)seen',a)
s=s[:a]+'''  uint8_t regs[512];uint64_t entries;fork_regs(regs,&entries);
  if(pthread_join(worker,NULL))abort();
  unsigned diff=0,extra=0,nonstack=0,rd=0,changes=0;
  for(unsigned j=0;j<num;j++){unsigned at=written[j];if(copy_[at]!=base[at]){diff++;nonstack+=!(at>=initial_sp-16384 && at<initial_sp+4);if(diff<5)fprintf(stderr,"[CLONE_DIFF] %08x %02x:%02x sp=%08x\\n",at,copy_[at],base[at],initial_sp);}}
  for(unsigned page=0;page<RAM;page+=4096){if(!memcmp(copy_+page,initial+page,4096))continue;
   for(unsigned j=page;j<page+4096;j++)if(copy_[j]!=initial[j]){changes++;extra+=!seen[j];}}
  for(unsigned j=0;j<nr;j++)rd+=regs[j]!=outregs[j];
  fprintf(stderr,"[WORKER_NATIVE] frame=%u actor=%u error=%08x original_writes=%u changed=%u byte_diff=%u nonstack=%u unseen_writes=%u regs=%u tickets=%llu:%llu entries=%llu:%llu\\n",frame,id,err,num,changes,diff,nonstack,extra,rd,(unsigned long long)(ngb_guest_polls-p0),(unsigned long long)(ticks-p0),(unsigned long long)(entries-e0),(unsigned long long)ent);
'''+s[b:]
s=s.replace('if(s && (frame==1802||frame==1808))','if(s && frame>=1802 && frame<=1810 && (i==0||i==21||i==4||i==7))')
print(s)
