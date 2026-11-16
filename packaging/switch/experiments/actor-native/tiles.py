"""Publish any interval, regardless of poll phase: compact eight polls per
immutable tile. Apply its ragged prefix and suffix from the ordered byte log.
Writes to adjacent bytes remain masked. No assumption about callback length."""
from pathlib import Path
import subprocess as sp,sys
here=Path(__file__).resolve().parent
s=sp.check_output([sys.executable,here/'prepared.py'],text=True)
s=s.replace('if((ticks-events+t)%64 && t!=events)continue;', 'if(t%8 && t!=events)continue;')
a=s.index('    while(block<blocks&&btick[block]<k)');b=s.index('flushes++;audit_before',a) if 'flushes++;audit_before' in s[a:] else s.index('flushes++;actor_stress_event',a)
s=s[:a]+'''    while(preok && block<blocks && btick[block]<=k && btick[block]<events){
     unsigned start=block?rend[block-1]:0;
     if(cursor==start){retire_prepared(block,base);retired+=pend[block]-(block?pend[block-1]:0);fast++;}
     else while(cursor<rend[block]){uint32_t *e=write_log[cursor++];base[e[1]]=e[2];retired++;}
     cursor=rend[block++];
    }
    while(cursor<nlog && write_log[cursor][0]<k){uint32_t *e=write_log[cursor++];base[e[1]]=e[2];retired++;}
    '''+s[b:]
a=s.index('  for(;cursor<nlog;cursor++){uint32_t*e=write_log[cursor];if(!store_byte');b=s.index('  fprintf(stderr,"[COMPACT_LIVE]',a)
s=s[:a]+'''  while(preok && block<blocks){
   if(cursor==(block?rend[block-1]:0)){retire_prepared(block,base);retired+=pend[block]-(block?pend[block-1]:0);fast++;}
   else while(cursor<rend[block]){uint32_t*e=write_log[cursor++];base[e[1]]=e[2];retired++;}
   cursor=rend[block++];}
  for(;cursor<nlog;cursor++){uint32_t*e=write_log[cursor];base[e[1]]=e[2];retired++;}
'''+s[b:]
print(s)
