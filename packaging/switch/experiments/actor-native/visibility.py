"""Check which in-progress actor bytes OTHER fibers/IRQs actually read.
Compare their live loads against a counterfactual RAM in which actor writes
are deferred. Other tasks' own writes become visible immediately. Reports
only instrumented CPU loads, not uninstrumented native or device accesses."""
from pathlib import Path
import subprocess as sp,sys
here=Path(__file__).resolve().parent;s=sp.check_output([sys.executable,here/'consume.py','--stress'],text=True)
i=s.index('extern void actor_commit_events')
s=s[:i]+'''static uint8_t *stale,*external;static uint32_t touched[131072];
static unsigned nt,checking,bytes_observed,loads,wrong,stack_wrong;
static void shadow_byte(unsigned a){if(!external[a]){if(nt==131072)abort();touched[nt++]=a;external[a]=1;stale[a]=base[a];}}
'''+s[i:]
s=s.replace('unsigned cursor=0;scope=0;', '''unsigned cursor=0;if(!stale){stale=malloc(RAM);external=calloc(RAM,1);if(!stale||!external)abort();}
  for(unsigned j=0;j<nt;j++)external[touched[j]]=0;nt=bytes_observed=loads=wrong=stack_wrong=0;scope=0;''')
s=s.replace('base[e[1]]=e[2];}\n   actor_stress_event(trace[k],nr);','''shadow_byte(e[1]);if(external[e[1]]==2){stale[e[1]]=base[e[1]];external[e[1]]=1;}base[e[1]]=e[2];}
   checking=1;actor_stress_event(trace[k],nr);checking=0;''')
s=s.replace('  actor_stress_final(outregs);','''  actor_stress_final(outregs);
  fprintf(stderr,"[EXPOSED] id=%u ext_loads=%u overlap_bytes=%u wrong=%u wrong_stack=%u\\n",id,loads,bytes_observed,wrong,stack_wrong);''')
tag=' (void)pc;if(!wr||!scope';assert tag in s
s=s.replace(tag,''' if(checking){uintptr_t off=(uintptr_t)ptr-(uintptr_t)base;if(n&&n<=RAM&&off<=RAM-n){
  loads+=!wr;for(unsigned j=0;j<n;j++){unsigned a=off+j;if(!external[a])continue;
   if(wr){external[a]=2;continue;}if(external[a]!=1)continue;bytes_observed++;if(stale[a]!=base[a]){wrong++;
    stack_wrong+=a>=initial_sp-16384&&a<initial_sp+4;
    if(wrong<=3)fprintf(stderr,"[EXPOSED_READ] id=%u address=%08x pc=%lx\\n",id,a,(unsigned long)pc);}
  }}return;}
'''+tag)
print(s)
