/* Observe the existing scalar decoder's eligibility without altering its decision. */
extern uint32_t opening_end4[];
static struct we_row {uint32_t count[2],slow[2],cross[2],alias[2];} we_rows[5][65536];
static _Thread_local unsigned we_phase;
static uint32_t we_pages[2][1u<<20];
void ws_observe(unsigned u,unsigned site,unsigned va){
 if(!we_phase)return;
 unsigned k=we_phase-1,pg=va>>12;
 struct we_row*r=&we_rows[u][site];++r->count[k];r->alias[k]+=(va>>31);
 if(va>=opening_end4[pg]){++r->slow[k];r->cross[k]+=(va&4095)>4092;++we_pages[k][pg];}
}
void phase_flip(unsigned f){
 if(!f)we_phase=1;
 if(f==30)we_phase=2;
 if(f==120){we_phase=0;
 for(unsigned u=0;u<5;u++)for(unsigned j=0;j<65536;j++){
 const struct we_row*r=&we_rows[u][j];if(r->count[0]||r->count[1])fprintf(stderr,"[WE_SITE] %u %u %u %u %u %u %u %u %u %u\n",u,j,r->count[0],r->slow[0],r->cross[0],r->alias[0],r->count[1],r->slow[1],r->cross[1],r->alias[1]);}
 for(unsigned j=0;j<(1u<<20);j++)if(we_pages[0][j]||we_pages[1][j])fprintf(stderr,"[WE_PAGE] %x %u %u\n",j,we_pages[0][j],we_pages[1][j]);}
}
