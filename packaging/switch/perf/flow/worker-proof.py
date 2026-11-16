"""Generate a real pthread worker prototype. Snapshot at the loop boundary,
run each recorded actor's ordered memory program on workers, validate input
values and collect FINAL writes. No commits to the running game. A successful
trace replay does NOT imply a complete independent native actor implementation."""
from pathlib import Path
s=Path(__file__).with_name('actor-transactions.c').read_text()
s='#include <pthread.h>\n'+s
pos=s.index('static void flush')
s=s[:pos]+'''struct op {unsigned at; unsigned char val,wr;};struct tape {struct op*ops;unsigned used,cap;};
static struct tape tapes[128];static unsigned capture;
static void record(unsigned off,int wr,unsigned val){struct tape*t=tapes+seq;
 if(t->used==t->cap){t->cap=t->cap?t->cap*2:4096;t->ops=realloc(t->ops,t->cap*sizeof(*t->ops));if(!t->ops)abort();}
 t->ops[t->used++]=(struct op){off,val,wr};
}
static unsigned char *view[2],*mark[2];static unsigned bad[128],done[128],expected[128],checks[128];
static void *worker(void*arg){unsigned lane=(uintptr_t)arg;
 for(unsigned i=lane+1;i<=seq;i+=2){
  struct tape*t=&tapes[i];unsigned char*m=mark[lane],*v=view[lane];unsigned mismatch=0,count=0,hash=2166136261u;
  for(unsigned j=0;j<t->used;j++){struct op a=t->ops[j];unsigned off=a.at;
   if(a.wr){m[off]=1;v[off]=a.val;}
   else {unsigned val=m[off]?v[off]:snap[off];mismatch+=val!=a.val;}
  }
  for(unsigned j=0;j<t->used;j++){unsigned off=t->ops[j].at;if(!m[off])continue;
   m[off]=0;hash=(hash^off)*16777619u;hash=(hash^v[off])*16777619u;count++;}
  bad[i]=mismatch;done[i]=hash;checks[i]=count;
 }return NULL;
}
'''+s[pos:]
s=s.replace('memcpy(local+pending_at,base+pending_at,pending_n);','''memcpy(local+pending_at,base+pending_at,pending_n);
 if(capture)for(unsigned j=0;j<pending_n;j++)record(pending_at+j,1,base[pending_at+j]);''')
s=s.replace('if(!snap||!local||!seen)abort();','''for(unsigned i=0;i<2;i++){view[i]=calloc(RAM,1);mark[i]=calloc(RAM,1);if(!view[i] || !mark[i])abort();}
 if(!snap||!local||!seen)abort();''')
s=s.replace('if(s){if(!seq)', 'if(s){capture=1;if(!seq)')
s=s.replace('++work;for(unsigned j','if(!wr)for(unsigned j=0;j<n;j++)record(a+j,0,base[a+j]);\n ++work;for(unsigned j')
s=s.replace('if(stage){unsigned final=0','''if(stage){capture=0;unsigned hash=2166136261u;
  struct tape*t=&tapes[seq];unsigned char*m=mark[0];
  for(unsigned j=0;j<t->used;j++)if(t->ops[j].wr)m[t->ops[j].at]=1;
  for(unsigned j=0;j<t->used;j++){unsigned off=t->ops[j].at;if(!m[off])continue;m[off]=0;hash=(hash^off)*16777619u;hash=(hash^base[off])*16777619u;}expected[seq]=hash;
  unsigned final=0''')
s=s.replace('if(active)abort();seq=0;', '''if(active)abort();if(frame){
 pthread_t th[2];for(unsigned i=0;i<2;i++)if(pthread_create(th+i,NULL,worker,(void*)(uintptr_t)i))abort();
 for(unsigned i=0;i<2;i++)if(pthread_join(th[i],NULL))abort();
 for(unsigned i=1;i<=seq;i++){fprintf(stderr,"[WORKER_CHECK] frame=%u actor_iter=%u ops=%u read_diff=%u final_hash_equal=%u final_bytes=%u\\n",frame,i,tapes[i].used,bad[i],done[i]==expected[i],checks[i]);tapes[i].used=0;}
 }seq=0;''')
print(s)
