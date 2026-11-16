"""Do fibers or hardware callbacks modify bytes this actor will later read?
Compare the actual future read footprint around each real service call.
A last read after an intervening local overwrite is counted conservatively."""
from pathlib import Path
import subprocess as sp,sys
here=Path(__file__).resolve().parent
s=sp.check_output([sys.executable,here/'tiles.py'],text=True)
s=s.replace('uint32_t*,unsigned*);','uint32_t*,unsigned*,uint16_t*,uint32_t*,unsigned*);',1)
s=s.replace('static struct patch prepatch', '''static uint16_t *last_read;static uint32_t read_list[262144];static uint8_t saved_read[262144];
static unsigned nread,service_checks,mismatches,changed_services;
static struct patch prepatch''')
s=s.replace('(void)unused;err=ngb_actor_native','''(void)unused;if(!last_read)last_read=calloc(RAM,sizeof(*last_read));if(!last_read)abort();
 for(unsigned j=0;j<nread;j++)last_read[read_list[j]]=0;nread=0;err=ngb_actor_native''')
s=s.replace('write_log[0],&nlog);','write_log[0],&nlog,last_read,read_list,&nread);')
tag='flushes++;actor_stress_event(trace[k],nr);'
assert tag in s
s=s.replace(tag,'''flushes++;
    for(unsigned j=0;j<nread;j++)if(last_read[read_list[j]]>k)saved_read[j]=base[read_list[j]];
    actor_stress_event(trace[k],nr);
    unsigned diff=0;for(unsigned j=0;j<nread;j++)if(last_read[read_list[j]]>k){
     service_checks++;if(base[read_list[j]]!=saved_read[j]){
      if(!mismatches&&!diff)fprintf(stderr,"[READ_CHANGE] actor=%u poll=%u addr=%08x before=%02x after=%02x\\n",id,k,read_list[j],saved_read[j],base[read_list[j]]);diff++;}}
    mismatches+=diff;changed_services+=!!diff;''')
s=s.replace('scope=0;counting=0;\n  for(unsigned k=1;', 'scope=0;counting=0;service_checks=mismatches=changed_services=0;\n  for(unsigned k=1;')
s=s.replace('  actor_stress_final(outregs);','  actor_stress_final(outregs);fprintf(stderr,"[FUTURE_READ] actor=%u unique=%u checked=%u changes=%u services_with_changes=%u\\n",id,nread,service_checks,mismatches,changed_services);')
print(s)
