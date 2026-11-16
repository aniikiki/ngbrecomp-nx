"""Two truly concurrent ahead-of-time workers, then consume their outputs.
First traversal trains pages and checks full reference. Later groups run from
one sparse snapshot. Audit every observed external load/store while results
are deferred, retain original poll services. Experimental host replay only."""
from pathlib import Path
h=Path(__file__).resolve().parent;s=(h/'wave.c').read_text()
s=s.replace('unsigned*,uint8_t*);','unsigned*,uint8_t*,uint8_t*);',1)
s=s.replace('uint8_t *slots,*foot;', 'uint8_t *slots,*foot,*trace;')
s=s.replace('j->touched,&j->used,j->foot);','j->touched,&j->used,j->foot,j->trace);')
s=s.replace('j->foot=calloc','j->trace=malloc(8192*320);if(!j->trace)abort();j->foot=calloc')
s=s.replace('if(pos==join_at)for(unsigned i=0;i<2;i++)pthread_join(threads[i],NULL);','if(pos==join_at && waves==1)for(unsigned i=0;i<2;i++)pthread_join(threads[i],NULL);')
i=s.index('void actor_end(void)')
s=s[:i]+'''static unsigned consuming,service,externalreads,externalwrites,retirements;
static struct job*running_job;
extern int actor_service_due(void);extern void actor_quiet_poll(void);extern void actor_ordered_entry(unsigned char*,unsigned);
extern void actor_stress_event(unsigned char*,unsigned);extern void actor_stress_final(const unsigned char*);
int actor_replay(void){
 if(!on||!active||!phase||id==0||waves<=1)return 0;unsigned pos=1;while(pos<count&&jobs[pos].id!=id)pos++;if(pos==count)abort();
 if(pos==1)for(unsigned k=0;k<2;k++)pthread_join(threads[k],NULL);
 struct job*j=jobs+pos;if(j->err)return 0;
 running_job=j;externalreads=externalwrites=0;unsigned serviced=0;uint64_t en;union regs r;unsigned nr=fork_regs(r.bytes,&en);
 consuming=1;
 for(unsigned t=1;t<=j->polls;t++){uint8_t *v=j->trace+320*t;
   if(actor_service_due()){service=1;serviced++;actor_stress_event(v,nr);service=0;}
   else{actor_ordered_entry(v,nr);actor_quiet_poll();}}
 /* Merge only bytes this calculation changed relative to its input.
    Neighboring bytes that were modified by a different task stay intact. */
 unsigned bytes=0;
 for(unsigned k=0;k<j->used;k++){unsigned pg=j->touched[k],a=pg<<12,ps=pos>=6&&pg==(sp>>12)?jobs[pos-1].index[pg]:0;
  uint8_t *old=ps?jobs[pos-1].slots+4096*(ps-1):initial+a,*out=j->slots+k*4096;
  for(unsigned off=0;off<4096;off+=8){uint64_t x,y;memcpy(&x,old+off,8);memcpy(&y,out+off,8);if(x==y)continue;
   for(unsigned z=0;z<8;z++){unsigned addr=a+off+z;if(addr==sp+20||old[off+z]==out[off+z])continue;
    base[addr]=out[off+z];bytes++;}}}
 actor_stress_final(j->regs.bytes);
 fprintf(stderr,"[JOINED_WAVE] wave=%u pos=%u actor=%u polls=%llu served=%u changed=%u external_loads_on_output_pages=%u external_writes_on_input_pages=%u total=%u\\n",waves,pos,id,(unsigned long long)j->polls,serviced,bytes,externalreads,externalwrites,++retirements);
 return 1;
}
'''+s[i:]
s=s.replace(' if(phase&&on){',' if(phase&&on&&consuming){consuming=0;if(id==jobs[count-1].id)on=0;}else if(phase&&on){')
tag='(void)pc;if(!wr||';s=s.replace(tag,'''(void)pc;if(service){uintptr_t a=(uintptr_t)ptr-(uintptr_t)base;if(n&&a<RAM&&n<=RAM-a){
 for(unsigned pg=a>>12;pg<=((a+n-1)>>12);pg++){if(wr)externalwrites+=running_job->foot[pg]!=0;else externalreads+=running_job->index[pg]!=0;}}
 return;}if(!wr||''')
print(s)
