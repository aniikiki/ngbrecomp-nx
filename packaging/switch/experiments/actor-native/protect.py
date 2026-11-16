"""Trap any native access to an actor's output pages during real external
service. Includes uninstrumented host code (unlike the TSAN load observer).
First access temporarily unprotects the page; never infer untouched bytes on
a touched page. Linux development host only, never used by the Switch port."""
from pathlib import Path
import subprocess as sp,sys
here=Path(__file__).resolve().parent;s=sp.check_output([sys.executable,here/'consume.py','--stress'],text=True)
i=s.index('extern void actor_commit_events')
s=s[:i]+'''static volatile sig_atomic_t armed,pagetraps;
static volatile unsigned char guard_pages[32768];static unsigned lens,service_total,service_hit;static uint16_t list[32768];static unsigned char hitpages[32768];
static void page_fault(int sig,siginfo_t*info,void*ctx){
 uintptr_t off=(uintptr_t)info->si_addr-(uintptr_t)base;
 if(!armed||off>=RAM||!guard_pages[off>>12])_exit(128+sig);
 unsigned p=off>>12;guard_pages[p]=0;hitpages[p]=1;pagetraps++;
 if(syscall(SYS_mprotect,base+4096*p,4096,PROT_READ|PROT_WRITE))_exit(99);
}
static void setup_guards(void){
 if((uintptr_t)base&4095)abort();static unsigned installed;if(!installed){
 struct sigaction sa={0};sa.sa_flags=SA_SIGINFO|SA_RESTART;sigemptyset(&sa.sa_mask);sa.sa_sigaction=page_fault;if(sigaction(SIGSEGV,&sa,NULL))abort();installed=1;}
 lens=service_total=service_hit=0;memset(hitpages,0,sizeof hitpages);
 for(unsigned k=0;k<nlog;k++){unsigned p=write_log[k][1]>>12;if(!guard_pages[p]){guard_pages[p]=1;list[lens++]=p;}}
 for(unsigned k=0;k<lens;k++)guard_pages[list[k]]=0;
}
static void guard_before(void){pagetraps=0;armed=1;service_total++;
 for(unsigned k=0;k<lens;k++){unsigned p=list[k];guard_pages[p]=1;if(mprotect(base+p*4096,4096,PROT_NONE))abort();}}
static void guard_after(void){for(unsigned k=0;k<lens;k++){unsigned p=list[k];if(guard_pages[p]){
 if(mprotect(base+p*4096,4096,PROT_READ|PROT_WRITE))abort();guard_pages[p]=0;}}
 service_hit+=!!pagetraps;armed=0;}
'''+s[i:]
s=s.replace('unsigned cursor=0;scope=0;','unsigned cursor=0;setup_guards();scope=0;')
s=s.replace('   actor_stress_event(trace[k],nr);','''   extern int actor_service_due(void);int due=actor_service_due();
   if(due)guard_before();actor_stress_event(trace[k],nr);if(due)guard_after();''')
s=s.replace('  actor_stress_final(outregs);','''  actor_stress_final(outregs);unsigned hit=0;for(unsigned j=0;j<lens;j++)hit+=hitpages[list[j]];
  fprintf(stderr,"[PROTECTED] actor=%u pages=%u serviced=%u services_touching=%u pages_touched=%u\\n",id,lens,service_total,service_hit,hit);''')
print('#define _GNU_SOURCE\n#include <sys/syscall.h>\n'+s)
