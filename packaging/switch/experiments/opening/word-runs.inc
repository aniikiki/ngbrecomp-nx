extern uint32_t opening_end4[];
static const struct {unsigned prev;int delta;} wr_allow[5][65536]={
#include "/work/build/switch-runtime/core-perf/opening-word-runs/eligible.inc"
};
static _Thread_local struct {unsigned phase,valid,u,site,va;uint64_t all[2],page[2],hit[2];} wr;
static uint32_t wr_hits[5][65536][2];
void ws_observe(unsigned u,unsigned site,unsigned va){
 if(!wr.phase)return;
 unsigned k=wr.phase-1;wr.all[k]++;
 if(wr.valid && va>>12==wr.va>>12 && va<opening_end4[va>>12] && wr.va<opening_end4[va>>12]){
  wr.page[k]++;
  if(wr.u==u && wr_allow[u][site].prev==1+wr.site && wr.va+(unsigned)wr_allow[u][site].delta==va){
    wr.hit[k]++;wr_hits[u][site][k]++;
  }
 }
 wr.valid=1;wr.va=va;wr.site=site;wr.u=u;
}
void phase_flip(unsigned f){
 wr.valid=0;
 if(!f)wr.phase=1;
 if(f==30)wr.phase=2;
 if(f==120){wr.phase=0;
 for(unsigned k=0;k<2;k++)fprintf(stderr,"[WORD_RUN] %u %llu %llu %llu\n",k,(unsigned long long)wr.all[k],(unsigned long long)wr.page[k],(unsigned long long)wr.hit[k]);
 for(unsigned u=0;u<5;u++)for(unsigned i=0;i<65536;i++)if(wr_hits[u][i][1])fprintf(stderr,"[WORD_PAIR] %u %u %u\n",u,i,wr_hits[u][i][1]);}
}
