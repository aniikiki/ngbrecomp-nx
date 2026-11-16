/* Boyer-Moore proposes a page without storing a full histogram. Validation counts are exact. */
struct ws_row {uint32_t seen,page,votes,late,hits;};
static struct ws_row ws_rows[5][65536];
static _Thread_local unsigned ws_phase;
void ws_observe(unsigned u,unsigned site,unsigned va){
 if(!ws_phase)return;
 struct ws_row *r=&ws_rows[u][site];unsigned page=va>>12;
 #ifdef WS_EXACT_ADDRESS
 page=va;
#endif
 if(ws_phase==1){++r->seen;if(!r->votes){r->page=page;r->votes=1;}else if(r->page==page)++r->votes;else --r->votes;}
 else {++r->late;if(r->seen && r->votes && r->page==page)++r->hits;}
}
void phase_flip(unsigned f){
 if(!f){memset(ws_rows,0,sizeof ws_rows);ws_phase=1;}
 if(f==30)ws_phase=2;
 if(f==120){ws_phase=0;for(unsigned u=0;u<5;u++)for(unsigned j=0;j<65536;j++){
 const struct ws_row*r=&ws_rows[u][j];if(r->seen||r->late)fprintf(stderr,"[WS_SITE] %u %u %u %x %u %u %u\n",u,j,r->seen,r->page,r->votes,r->late,r->hits);}}
}
