"""Split parent scheduling counters at the exact Xbox context switches.
Compare actor-only ticket/entry counts with the isolated CPU replay."""
from pathlib import Path
s=Path(__file__).with_name('actor-fork.c').read_text()
s=s.replace('void dep_key(unsigned k){active=', '''static uint64_t charged_p,charged_e,start_p,start_e;static unsigned counting;
static uint64_t entry_now(void){extern uint64_t fork_entries(void);return fork_entries();}
void dep_key(unsigned k){
 if(counting){charged_p+=ngb_guest_polls-start_p;charged_e+=entry_now()-start_e;counting=0;}
 active=''')
s=s.replace('if(active){stage=k>>8&1;id=k&63;}}','if(active){stage=k>>8&1;id=k&63;}if(scope&&active&&stage){counting=1;start_p=ngb_guest_polls;start_e=entry_now();}}')
s=s.replace('p0=ngb_guest_polls;','p0=ngb_guest_polls;charged_p=charged_e=0;counting=1;start_p=p0;start_e=e0;')
s=s.replace('  if(actor_fork_child){result->n=', '''  if(counting){charged_p+=ngb_guest_polls-start_p;charged_e+=entries-start_e;counting=0;}
  if(actor_fork_child){result->n=''')
s=s.replace('result->tickets=ngb_guest_polls-p0;result->entries=entries-e0','result->tickets=charged_p;result->entries=charged_e')
s=s.replace('(unsigned long long)(ngb_guest_polls-p0),result->tickets,(unsigned long long)(entries-e0)','(unsigned long long)charged_p,result->tickets,(unsigned long long)charged_e')
print(s.replace('[NATIVE_ACTOR]','[NATIVE_ACCOUNT]'))
