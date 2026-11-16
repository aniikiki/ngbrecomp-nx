"""Drop-in experimental topology for critical-path.py: half the parent
calculation stays on the owner CPU, one persistent worker handles the
dependency chain. No per-frame thread creation and no busy-spin joining."""
from pathlib import Path
def transform(s):
 a=s.index('static void *worker(');b=s.index('/* Measure the same',a)
 s=s[:a]+'''static pthread_t background;static pthread_barrier_t launch,done;static unsigned live_pool;
static void *background_loop(void*unused){
 for(;;){pthread_barrier_wait(&launch);for(unsigned k=5;k<count;k++)calc(k);pthread_barrier_wait(&done);}return NULL;
}
static void start_jobs(void){if(!live_pool){pthread_barrier_init(&launch,NULL,2);pthread_barrier_init(&done,NULL,2);
 if(pthread_create(&background,NULL,background_loop,NULL))abort();live_pool=1;}
 pthread_barrier_wait(&launch);for(unsigned k=1;k<5&&k<count;k++)calc(k);}
static void join_jobs(void){pthread_barrier_wait(&done);}
'''+s[b:]
 s=s.replace('for(unsigned i=0;i<2;i++)if(pthread_create(threads+i,NULL,worker,NULL))abort();','start_jobs();')
 s=s.replace('for(unsigned i=0;i<2;i++)pthread_join(threads[i],NULL);','join_jobs();').replace('for(unsigned k=0;k<2;k++)pthread_join(threads[k],NULL);','join_jobs();')
 return s
