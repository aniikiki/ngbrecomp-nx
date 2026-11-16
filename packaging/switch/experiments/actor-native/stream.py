"""Apply the worker's per-poll masked stores without a byte journal, waiting
only at actual guest service points. A callback's change to adjacent bytes is
preserved. Diagnostic consumes jobs only during specified combat window."""
from pathlib import Path
import subprocess as sp,sys
here=Path(__file__).resolve().parent;s=sp.check_output([sys.executable,here/'compact-live.py'],text=True)
a=s.index('  static struct packer pack;');b=s.index('  actor_stress_final(outregs);',a)
s=s[:a]+'''  unsigned cursor=0,flushes=0,bytes=0;scope=0;counting=0;
  for(unsigned k=1;k<=events+1;k++){
   int end=k>events;
   if(end||actor_service_due()){
    while(cursor<nlog && (end|| (write_log[cursor][0]>>4)<k)){uint32_t *e=write_log[cursor++];unsigned mask=e[0]&15;uint8_t *p=base+e[1];
     if(mask==15){memcpy(p,e+2,4);bytes+=4;}
     else for(unsigned z=0;z<4;z++)if(mask&(1u<<z)){p[z]=e[2]>>(z*8);bytes++;}}
    if(!end){flushes++;actor_stress_event(trace[k],nr);}
   }else{actor_ordered_entry(trace[k],nr);actor_quiet_poll();}
  }
  fprintf(stderr,"[STREAM_LIVE] actor=%u checks=%u services=%u records=%u bytes=%u\\n",id,events,flushes,nlog,bytes);
'''+s[b:]
print(s)
