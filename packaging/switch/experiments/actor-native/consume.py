"""Offline, gated replacement of a live actor calculation. One can commit only
when no poll callback is due before its end. Never deploy this verifier."""
from pathlib import Path
import subprocess as sp,sys
s=sp.check_output([sys.executable,Path(__file__).with_name('journal-shadow.py')],text=True)
# Narrowly scoped experiment. No asynchronous writes can occur in the calling
# game's cooperative thread before a due poll. Avoid observing other actors.
if '--stress' in sys.argv:s=s.replace('i==0||i==21||i==4||i==7','i==0||i==4||i==7||i==21')
s=s.replace('i==0||i==21||i==4||i==7','i==1||i==23')
s=s.replace('extern uint64_t ngb_guest_polls;', 'extern uint64_t ngb_guest_polls;extern unsigned ngb_pending_dpcs,ngb_poll_mask;')
s=s.replace('frame<=1810','frame<=1820')
a=s.index('void actor_end(void)')
s=s[:a]+'''extern void actor_commit_events(unsigned char*,unsigned,unsigned,const unsigned char*,uint64_t);
static unsigned replaced;
int actor_replay(void){
 if(!active||!stage||!scope)return 0;
 static int checked_stress;static unsigned admit; if(!checked_stress){checked_stress=1;admit=getenv("NGB_STRESS_IRQ_REPLAY")!=NULL;}
 /* Non-preemptive window only. Unchanged pending flag and ticket make the
    admission independent of actual wall time or IRQ state. */
 if(!admit && (!(id==1||id==23) || ngb_pending_dpcs || ngb_poll_mask!=63 || (p0&63)>21))return 0;
 if(pthread_join(worker,NULL))abort();
 unsigned markers=0;for(unsigned k=1;k<=events;k++){uint32_t pc;memcpy(&pc,trace[k]+nr,4);markers+=pc>>31;}
 unsigned allowed=markers==ent && !err&&events==ticks-p0&&(admit || events<=ngb_poll_mask-(p0&ngb_poll_mask))&&p0==ngb_guest_polls;
 if(!allowed){/* Original shadow close normally joins; start a fresh identical job. */
    memcpy(copy_,initial,RAM);memcpy(outregs,inregs,nr);ticks=p0;ent=0;
    if(pthread_create(&worker,NULL,run_actor,NULL))abort();return 0;}
 if(admit){
  extern void actor_stress_event(unsigned char*,unsigned);
  extern void actor_stress_final(const unsigned char*);
  unsigned cursor=0;scope=0;counting=0;
  for(unsigned k=1;k<=events;k++){while(cursor<nlog&&write_log[cursor][0]<k){uint32_t*e=write_log[cursor++];base[e[1]]=e[2];}
   actor_stress_event(trace[k],nr);}
  for(;cursor<nlog;cursor++){uint32_t*e=write_log[cursor];base[e[1]]=e[2];}
  actor_stress_final(outregs);
 }else{
 for(unsigned k=0;k<nlog;k++){uint32_t*e=write_log[k];if(e[1]>=RAM)abort();base[e[1]]=e[2];}
 actor_commit_events(trace[0],520,events,outregs,ticks);
 }
 replaced++;fprintf(stderr,"[LIVE_REPLACED] waveframe=%u actor=%u events=%u entries=%llu writes=%u total=%u\\n",frame,id,events,(unsigned long long)ent,nlog,replaced);
 scope=0;counting=0;return 1;
}
'''+s[a:]
s=s.replace('static uint8_t outregs[512];','static uint8_t inregs[512],outregs[512];').replace('nr=fork_regs(outregs,&e0);','nr=fork_regs(outregs,&e0);memcpy(inregs,outregs,nr);')
print(s)
