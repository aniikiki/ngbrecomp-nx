"""Rapid check of final memory reconstructed solely from the timestamped byte
journal of the devkit worker against captured original stores and registers."""
from pathlib import Path
import subprocess as sp
here=Path(__file__).resolve().parent;d=Path('/work/build/switch-runtime/opt050/actor-journal')
s=(here/'replay.c').read_text().replace('uint64_t*,uint64_t*);','uint64_t*,uint64_t*,uint8_t*,unsigned,unsigned*,uint32_t*,unsigned*);',1)
a=' j->error=ngb_actor_native(j->regs,j->ram,j->pages,&j->ticks,&j->entries);'
b=''' uint8_t *trace=malloc(8192*520);uint32_t (*writes)[3]=malloc(524288*12);unsigned events=0,n=0;if(!trace||!writes)abort();
 j->error=ngb_actor_native(j->regs,j->ram,j->pages,&j->ticks,&j->entries,trace,520,&events,writes[0],&n);
 memcpy(j->ram,j->init,RAM);
 for(unsigned k=0;k<n;k++){if(writes[k][1]>=RAM||writes[k][0]>events)abort();j->ram[writes[k][1]]=writes[k][2];}
 printf("[JOURNAL_REPLAY] id=%u polls=%u stores=%u\\n",j->meta[2],events,n);
 free(trace);free(writes);'''
assert a in s;s=s.replace(a,b);(d/'standalone.c').write_text(s);sp.run(['cc','-O2','-I'+str(here),d/'standalone.c',d/'actor.o',d.parent.parent/'core-perf/thread-pointer.o','-l:libz.so.1','-pthread','-lm','-o',d/'standalone'],check=True)
