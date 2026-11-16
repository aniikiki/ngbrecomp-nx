"""Audit intervening real game/IRQ code while publishing finished actor
results. A later read by isolated code is relevant only BEFORE that code
rewrites the byte. This first probe measures overlap with the worker's write pages only;
it is not a proof of read isolation."""
from pathlib import Path
import subprocess as sp,sys
here=Path(__file__).resolve().parent
s=sp.check_output([sys.executable,here/'prepared.py'],text=True)
# Observer captures the pre-write value at first tracked store; compare to
# actual RAM after the cooperative guest resumes. Values restored in the
# interim do not invalidate a future read. Not all uninstrumented I/O is seen.
a=s.index('extern void actor_commit_events')
s=s[:a]+'''static int auditing;static uint8_t footprint[32768],prior_value[131072],*first_seen;
static uint32_t external_at[131072];static unsigned external_n,overlap,changes,external_stores;
static void audit_before(void){auditing=1;external_n=0;}
static void audit_after(void){
 auditing=0;for(unsigned k=0;k<external_n;k++){unsigned a=external_at[k];first_seen[a]=0;
  if(base[a]!=prior_value[k]){changes++;overlap+=footprint[a>>12]!=0;}}
}
'''+s[a:]
s=s.replace('  scope=0;counting=0;', '''  if(!first_seen)first_seen=calloc(RAM,1);if(!first_seen)abort();
  memset(footprint,0,sizeof footprint);for(unsigned j=0;j<nlog;j++)footprint[write_log[j][1]>>12]=1;
  overlap=changes=external_stores=0;scope=0;counting=0;''')
s=s.replace('flushes++;actor_stress_event(trace[k],nr);','flushes++;audit_before();actor_stress_event(trace[k],nr);audit_after();')
s=s.replace('  actor_stress_final(outregs);','  actor_stress_final(outregs);fprintf(stderr,"[INTERVENING] actor=%u stores=%u changed=%u changed_on_worker_write_pages=%u\\n",id,external_stores,changes,overlap);')
a=' (void)pc;if(!wr||!scope'
assert a in s
s=s.replace(a,''' if(auditing&&wr){uintptr_t off=(uintptr_t)ptr-(uintptr_t)base;if(n&&n<=RAM&&off<=RAM-n){
  external_stores+=n;for(unsigned k=0;k<n;k++){unsigned a=off+k;if(first_seen[a])continue;
   if(external_n==131072)abort();first_seen[a]=1;external_at[external_n]=a;prior_value[external_n++]=base[a];}}
  return;}
 (void)pc;if(!wr||!scope''')
print(s)
