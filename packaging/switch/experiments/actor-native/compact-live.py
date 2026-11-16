"""Replay an isolated worker's writes only at poll service boundaries.
Between them the cooperative guest cannot observe the intermediate writes.
Use the game's actual poll phase after each callback, not a fixed schedule."""
from pathlib import Path
import subprocess as sp,sys
here=Path(__file__).resolve().parent
s=sp.check_output([sys.executable,here/'consume.py','--stress'],text=True)
a=s.index('  unsigned cursor=0;scope=0;');b=s.index('  actor_stress_final(outregs);',a)
s=s[:a]+'''  extern int actor_service_due(void);
  extern void actor_ordered_entry(unsigned char*,unsigned);
  extern void actor_quiet_poll(void);
  static struct packer pack;if(pack.used)abort();unsigned cursor=0,flushes=0,retired=0;
  scope=0;counting=0;
  for(unsigned k=1;k<=events;k++){
   if(actor_service_due()){
    while(cursor<nlog&&write_log[cursor][0]<k){uint32_t*e=write_log[cursor++];
     if(!store_byte(&pack,e[1],e[2]))abort();}
    retired+=pack.used;apply(&pack,base);flushes++;actor_stress_event(trace[k],nr);
   }else{actor_ordered_entry(trace[k],nr);actor_quiet_poll();}
  }
  for(;cursor<nlog;cursor++){uint32_t*e=write_log[cursor];if(!store_byte(&pack,e[1],e[2]))abort();}
  retired+=pack.used;apply(&pack,base);
  fprintf(stderr,"[COMPACT_LIVE] actor=%u checks=%u served=%u raw_bytes=%u masked_words=%u\\n",id,events,flushes,nlog,retired);
'''+s[b:]
print((here/'packed-trace.c').read_text()+'\n'+s)
