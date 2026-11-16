"""Run two separate sparse native contexts concurrently; compare the merged
dirty pages and registers against original captures, then benchmark warm jobs."""
from pathlib import Path
import subprocess as sp
d=Path('/work/build/switch-runtime/opt050/actor-sparse');here=Path(__file__).resolve().parent
s=(here/'replay.c').read_text()
s=s.replace('struct job {','extern unsigned ngb_actor_sparse(void*,unsigned char*,const uint16_t*,uint64_t*,uint64_t*,uint16_t*,unsigned char*,uint16_t*,unsigned*);\nstruct job {uint16_t *index,*touched;uint8_t *slots;unsigned used;')
s=s.replace('j->ram=malloc(RAM);','j->index=calloc(32768,2);j->touched=malloc(512*2);j->slots=malloc(512*4096);if(!j->index||!j->touched||!j->slots)return 0;j->ram=malloc(RAM);')
s=s.replace('j->error=ngb_actor_native(j->regs,j->ram,j->pages,&j->ticks,&j->entries);','''uint8_t r0[512];memcpy(r0,j->regs,j->meta[3]);uint64_t polls=j->ticks;
 unsigned loops=64;for(unsigned k=0;k<loops;k++){
  for(unsigned j_=0;j_<j->used;j_++)j->index[j->touched[j_]]=0;
  j->used=0;memcpy(j->regs,r0,j->meta[3]);j->ticks=polls;j->entries=0;
  j->error=ngb_actor_sparse(j->regs,j->init,j->pages,&j->ticks,&j->entries,j->index,j->slots,j->touched,&j->used);
  if(j->error)break;
 }''').replace('b.tv_nsec-a.tv_nsec;return 0;', '''b.tv_nsec-a.tv_nsec;j->ns/=loops;
 for(unsigned i=0;i<j->used;i++)memcpy(j->ram+4096u*j->touched[i],j->slots+4096u*i,4096);return 0;''').replace('[ACTOR_JOB] frame=%u','[SPARSE_JOB] pages=%u frame=%u').replace('v->meta[1],v->meta[2],v->error','v->used,v->meta[1],v->meta[2],v->error')
(d/'test.c').write_text(s)
sp.run(['cc','-O2','-I'+str(here),d/'test.c',d/'actor.o',d.parent.parent/'core-perf/thread-pointer.o','-pthread','-l:libz.so.1','-lm','-o',d/'replay'],check=True)
