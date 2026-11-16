"""Two captured actor jobs, SAME calculations and inputs, serial vs two warm
persistent workers. Times include job handoff, barrier, sparse page work and
original register accounting, exclude asset loading and whole-frame simulation."""
from pathlib import Path
import subprocess as sp
here=Path(__file__).resolve().parent;d=Path('/work/build/switch-runtime/opt050/actor-sparse')
s=(d/'test.c').read_text();a=s.index('static void *run(');b=s.index('int main(',a)
s=s[:a]+'''static void calc(struct job*j,const uint8_t*r,uint64_t p){
 for(unsigned k=0;k<j->used;k++)j->index[j->touched[k]]=0;
 j->used=0;memcpy(j->regs,r,j->meta[3]);j->ticks=p;j->entries=0;
 j->error=ngb_actor_sparse(j->regs,j->init,j->pages,&j->ticks,&j->entries,j->index,j->slots,j->touched,&j->used);if(j->error)abort();
}
static pthread_barrier_t start,end;static unsigned stop,enabled;
static struct job *other;static uint8_t initialregs[2][512];static uint64_t initialpoll[2];
static void* worker(void *arg){for(;;){pthread_barrier_wait(&start);if(stop)return NULL;
 calc(other,initialregs[1],initialpoll[1]);pthread_barrier_wait(&end);}}
static uint64_t clock_ns(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec*1000000000ull+t.tv_nsec;}
'''+s[b:]
a=s.index(' for(int i=0;i<argc-1;i++)if(pthread_create');b=s.index(' for(int i=0;i<argc-1;i++){struct job*v=',a)
s=s[:a]+''' if(argc!=3)return 2;
 for(unsigned i=0;i<2;i++){memcpy(initialregs[i],j[i].regs,j[i].meta[3]);initialpoll[i]=j[i].ticks;}
 pthread_barrier_init(&start,0,2);pthread_barrier_init(&end,0,2);other=j+1;if(pthread_create(threads,0,worker,0))abort();
 for(unsigned round=0;round<68;round++){
  unsigned order=round%4==1||round%4==2;uint64_t times[2];
  for(unsigned sub=0;sub<2;sub++){
   unsigned par=order^sub;uint64_t before=clock_ns();
   for(unsigned it=0;it<32;it++){if(par)pthread_barrier_wait(&start);
    calc(j,initialregs[0],initialpoll[0]);
    if(par)pthread_barrier_wait(&end);else calc(j+1,initialregs[1],initialpoll[1]);}
   times[par]=clock_ns()-before;
  }
  if(round>=4)printf("[THREAD_PAIR] %u %llu %llu\\n",round,(unsigned long long)times[0],(unsigned long long)times[1]);
 }
 stop=1;pthread_barrier_wait(&start);pthread_join(threads[0],NULL);
 for(unsigned i=0;i<2;i++)for(unsigned k=0;k<j[i].used;k++)memcpy(j[i].ram+4096u*j[i].touched[k],j[i].slots+4096u*k,4096);
'''+s[b:]
(d/'bench.c').write_text(s);sp.run(['cc','-O2','-I'+str(here),d/'bench.c',d/'actor.o',d.parent.parent/'core-perf/thread-pointer.o','-pthread','-l:libz.so.1','-lm','-o',d/'bench'],check=True)
