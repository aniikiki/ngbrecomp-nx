"""Measure how much of the machine state really changes at observable polls,
before designing a production replay format. Uses captured, private job files."""
from pathlib import Path
import subprocess as sp
here=Path(__file__).resolve().parent;d=Path('/work/build/switch-runtime/opt050/actor-journal')
s=(d/'standalone.c').read_text()
a=' memcpy(j->ram,j->init,RAM);'
b=''' uint64_t saved=0,keys=0,changedmem=0,memoryruns=0,gpr=0,group=0;
 uint32_t *last=calloc(RAM/4,4);if(!last)abort();
 unsigned cursor=0,prev=0;
 for(unsigned k=1;k<=events;k++){
  if(((j->ticks-events+k)&63)&&k!=events)continue;
  unsigned nw=0;
  while(cursor<n&&writes[cursor][0]<k){
   unsigned addr=writes[cursor][1],idx=addr/4;if(last[idx]!=k){nw++;last[idx]=k;}
   j->ram[addr]=writes[cursor++][2];
  }
  for(unsigned x=0;x<j->meta[3];x+=4)if(!prev||memcmp(trace+520*k+x,trace+520*prev+x,4))gpr++;
  keys+=nw;group++;prev=k;
 }
 printf("[TRACE_WIDTH] id=%u boundaries=%llu word_destinations=%llu register_words=%llu raw_stores=%u\\n",j->meta[2],(unsigned long long)group,(unsigned long long)keys,(unsigned long long)gpr,n);
 free(last);
'''+a
assert s.count(a)==1;s=s.replace(a,b)
(d/'width.c').write_text(s)
sp.run(['cc','-O2','-I'+str(here),d/'width.c',d/'actor.o',d.parent.parent/'core-perf/thread-pointer.o','-l:libz.so.1','-pthread','-lm','-o',d/'width'],check=True)
