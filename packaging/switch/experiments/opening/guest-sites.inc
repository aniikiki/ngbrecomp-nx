unsigned stream_on;
static struct {uint32_t ret,va,n;} guest_sites[32768];
static unsigned site_visits,site_bad,site_drop;
void stream_visit(uint32_t va,uint32_t sp,const uint8_t *ram,const uint32_t *ends){
 ++site_visits;
 if(sp>64u*1024u*1024u-4 || sp>=ends[sp>>12]){++site_bad;return;}
 uint32_t ret; memcpy(&ret,ram+sp,4);
 unsigned j=((ret*2654435761u)^(va*2246822519u))>>17;
 for(unsigned i=0;i<128;i++,j=(j+1)&32767){
  if(!guest_sites[j].n){guest_sites[j].ret=ret;guest_sites[j].va=va;}
  if(guest_sites[j].ret==ret && guest_sites[j].va==va){++guest_sites[j].n;return;}
 }
 ++site_drop;
}
void phase_flip(unsigned f){
 if(f==30||f==120){
  unsigned total=0;
  for(unsigned i=0;i<32768;i++)if(guest_sites[i].n){
    total+=guest_sites[i].n;
    fprintf(stderr,"[GUEST_SITE] %u %x %x %u\n",f,guest_sites[i].ret,guest_sites[i].va,guest_sites[i].n);}
  if(total+site_bad+site_drop!=site_visits)abort();
  fprintf(stderr,"[SITE_TOTAL] %u %u %u %u\n",f,site_visits,site_bad,site_drop);
 }
 if(!f||f==30){memset(guest_sites,0,sizeof guest_sites);site_visits=site_bad=site_drop=0;}
 stream_on=f<120;
}
